from collections.abc import Sequence
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Row, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound, Unprocessable
from app.modules.auth.service import CurrentUser
from app.modules.evals.access import require_edit, require_view
from app.modules.evals.models import Dataset, DatasetCase, Prompt, PromptVersion, users
from app.modules.evals.schemas import (
    MAX_CASES,
    MAX_JSONL_BYTES,
    CaseIn,
    CaseOut,
    DatasetDetailOut,
    DatasetSummaryOut,
    PromptDetailOut,
    PromptSummaryOut,
    VersionIn,
    VersionOut,
)

COPY_SUFFIX = " (копия)"
MAX_NAME = 200

_latest_version = (
    select(func.max(PromptVersion.number))
    .where(PromptVersion.prompt_id == Prompt.id)
    .scalar_subquery()
)
# Prompt, owner login, latest version number
_summary_query = select(Prompt, users.c.login, _latest_version).join(
    users, users.c.id == Prompt.owner_id
)


def _copy_name(name: str) -> str:
    return name[: MAX_NAME - len(COPY_SUFFIX)] + COPY_SUFFIX


def _summary(row: Row[Prompt, str, int]) -> PromptSummaryOut:
    prompt, owner_login, latest_version = row
    return PromptSummaryOut(
        id=prompt.id,
        name=prompt.name,
        shared=prompt.shared,
        owner_login=owner_login,
        latest_version=latest_version,
        created_at=prompt.created_at,
    )


class PromptService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user: CurrentUser,
        name: str,
        version: VersionIn,
        trainer_task: str | None = None,
    ) -> PromptDetailOut:
        prompt = Prompt(owner_id=user.id, name=name, trainer_task=trainer_task)
        self.session.add(prompt)
        await self.session.flush()
        self.session.add(
            PromptVersion(prompt_id=prompt.id, number=1, created_by=user.id, **version.model_dump())
        )
        await self.session.commit()
        return await self.get(user, prompt.id)

    async def add_version(
        self, user: CurrentUser, prompt_id: UUID, version: VersionIn
    ) -> VersionOut:
        # the row lock serialises writers, so numbers stay gap-free under UNIQUE(prompt_id, number)
        prompt = await self.session.scalar(
            select(Prompt).where(Prompt.id == prompt_id).with_for_update()
        )
        require_edit(prompt, user.id)
        number = await self.session.scalar(
            select(func.coalesce(func.max(PromptVersion.number), 0) + 1).where(
                PromptVersion.prompt_id == prompt_id
            )
        )
        assert number is not None
        row = PromptVersion(
            prompt_id=prompt_id, number=number, created_by=user.id, **version.model_dump()
        )
        self.session.add(row)
        await self.session.commit()
        return VersionOut.model_validate(row)

    async def get(self, user: CurrentUser, prompt_id: UUID) -> PromptDetailOut:
        row = (await self.session.execute(_summary_query.where(Prompt.id == prompt_id))).first()
        require_view(row[0] if row else None, user.id)
        assert row is not None  # require_view raised otherwise
        versions = await self.session.scalars(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(PromptVersion.number)
        )
        return PromptDetailOut(
            **_summary(row).model_dump(), versions=[VersionOut.model_validate(v) for v in versions]
        )

    async def list(self, user: CurrentUser) -> list[PromptSummaryOut]:
        rows = await self.session.execute(
            _summary_query.where(
                or_(Prompt.owner_id == user.id, Prompt.shared), Prompt.trainer_task.is_(None)
            ).order_by(Prompt.created_at.desc(), Prompt.name)
        )
        return [_summary(r) for r in rows]

    async def update(
        self, user: CurrentUser, prompt_id: UUID, name: str | None, shared: bool | None
    ) -> PromptSummaryOut:
        prompt = require_edit(await self.session.get(Prompt, prompt_id), user.id)
        if name is not None:
            prompt.name = name
        if shared is not None:
            prompt.shared = shared
        await self.session.commit()
        row = (await self.session.execute(_summary_query.where(Prompt.id == prompt_id))).one()
        return _summary(row)

    async def copy(self, user: CurrentUser, prompt_id: UUID) -> PromptDetailOut:
        source = await self.get(user, prompt_id)
        latest = VersionIn.model_validate(source.versions[-1].model_dump())
        return await self.create(user, _copy_name(source.name), latest)

    async def get_version(self, user: CurrentUser, version_id: UUID) -> VersionOut:
        version = await self.session.get(PromptVersion, version_id)
        prompt = await self.session.get(Prompt, version.prompt_id) if version else None
        require_view(prompt, user.id)
        assert version is not None
        return VersionOut.model_validate(version)


_case_count = select(func.count()).where(DatasetCase.dataset_id == Dataset.id).scalar_subquery()
# Dataset, owner login, case count
_dataset_query = select(Dataset, users.c.login, _case_count).join(
    users, users.c.id == Dataset.owner_id
)


def _dataset_summary(row: Row[Dataset, str, int]) -> DatasetSummaryOut:
    dataset, owner_login, case_count = row
    return DatasetSummaryOut(
        id=dataset.id,
        name=dataset.name,
        shared=dataset.shared,
        owner_login=owner_login,
        case_count=case_count,
        created_at=dataset.created_at,
    )


def _case_rows(dataset_id: UUID, cases: Sequence[CaseIn]) -> list[DatasetCase]:
    return [
        DatasetCase(dataset_id=dataset_id, position=i, **c.model_dump())
        for i, c in enumerate(cases, 1)
    ]


def _parse_jsonl(raw: bytes) -> list[CaseIn]:
    if len(raw) > MAX_JSONL_BYTES:
        raise Unprocessable("Файл больше 5 МБ")
    try:
        text = raw.decode("utf-8-sig")  # drops a BOM
    except UnicodeDecodeError:
        raise Unprocessable("Файл не в кодировке UTF-8") from None
    # strip() drops the \r of CRLF; numbers count raw lines, blank ones included
    lines = [(n, s) for n, line in enumerate(text.split("\n"), 1) if (s := line.strip())]
    if len(lines) > MAX_CASES:
        raise Unprocessable(f"В датасете не больше {MAX_CASES} кейсов")
    cases: list[CaseIn] = []
    errors: list[str] = []
    for number, line in lines:
        try:
            cases.append(CaseIn.model_validate_json(line))
        except ValidationError as e:
            problems = (
                ".".join(map(str, p["loc"])) + ": " + p["msg"] if p["loc"] else p["msg"]
                for p in e.errors()
            )
            errors.append(f"Строка {number}: " + ", ".join(problems))
    if errors:
        raise Unprocessable("; ".join(errors))
    return cases


class DatasetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, user: CurrentUser, name: str, cases: Sequence[CaseIn] = ()
    ) -> DatasetDetailOut:
        dataset = Dataset(owner_id=user.id, name=name)
        self.session.add(dataset)
        await self.session.flush()
        self.session.add_all(_case_rows(dataset.id, cases))
        await self.session.commit()
        return await self.get(user, dataset.id)

    async def get(self, user: CurrentUser, dataset_id: UUID) -> DatasetDetailOut:
        row = (await self.session.execute(_dataset_query.where(Dataset.id == dataset_id))).first()
        require_view(row[0] if row else None, user.id)
        assert row is not None  # require_view raised otherwise
        cases = await self.session.scalars(
            select(DatasetCase)
            .where(DatasetCase.dataset_id == dataset_id)
            .order_by(DatasetCase.position)
        )
        return DatasetDetailOut(
            **_dataset_summary(row).model_dump(), cases=[CaseOut.model_validate(c) for c in cases]
        )

    async def update(
        self, user: CurrentUser, dataset_id: UUID, name: str | None, shared: bool | None
    ) -> DatasetSummaryOut:
        dataset = await self._for_edit(user, dataset_id)
        if name is not None:
            dataset.name = name
        if shared is not None:
            dataset.shared = shared
        await self.session.commit()
        row = (await self.session.execute(_dataset_query.where(Dataset.id == dataset_id))).one()
        return _dataset_summary(row)

    async def copy(self, user: CurrentUser, dataset_id: UUID) -> DatasetDetailOut:
        source = await self.get(user, dataset_id)
        cases = [CaseIn(variables=c.variables, expected=c.expected) for c in source.cases]
        return await self.create(user, _copy_name(source.name), cases)

    async def get_cases(self, user: CurrentUser, dataset_id: UUID) -> list[CaseIn]:
        require_view(await self.session.get(Dataset, dataset_id), user.id)
        rows = await self.session.scalars(
            select(DatasetCase)
            .where(DatasetCase.dataset_id == dataset_id)
            .order_by(DatasetCase.position)
        )
        return [CaseIn.model_validate(r, from_attributes=True) for r in rows]

    async def export_jsonl(self, user: CurrentUser, dataset_id: UUID) -> str:
        return "".join(c.model_dump_json() + "\n" for c in await self.get_cases(user, dataset_id))

    async def replace_cases(self, user: CurrentUser, dataset_id: UUID, raw: bytes) -> int:
        await self._for_edit(user, dataset_id)
        cases = _parse_jsonl(raw)  # nothing is written unless every line is valid
        await self.session.execute(delete(DatasetCase).where(DatasetCase.dataset_id == dataset_id))
        self.session.add_all(_case_rows(dataset_id, cases))
        await self.session.commit()
        return len(cases)

    async def add_case(self, user: CurrentUser, dataset_id: UUID, case: CaseIn) -> CaseOut:
        await self._for_edit(user, dataset_id)
        count, last = (
            await self.session.execute(
                select(func.count(), func.coalesce(func.max(DatasetCase.position), 0)).where(
                    DatasetCase.dataset_id == dataset_id
                )
            )
        ).one()
        if count >= MAX_CASES:
            raise Unprocessable(f"В датасете не больше {MAX_CASES} кейсов")
        row = DatasetCase(dataset_id=dataset_id, position=last + 1, **case.model_dump())
        self.session.add(row)
        await self.session.commit()
        return CaseOut.model_validate(row)

    async def update_case(
        self, user: CurrentUser, dataset_id: UUID, case_id: UUID, case: CaseIn
    ) -> CaseOut:
        await self._for_edit(user, dataset_id)
        row = await self._case(dataset_id, case_id)
        row.variables = case.variables
        row.expected = case.expected
        await self.session.commit()
        return CaseOut.model_validate(row)

    async def delete_case(self, user: CurrentUser, dataset_id: UUID, case_id: UUID) -> None:
        await self._for_edit(user, dataset_id)
        await self.session.delete(await self._case(dataset_id, case_id))
        await self.session.commit()

    # keep after every `list[...]` annotation: this method shadows the builtin in the class body
    async def list(self, user: CurrentUser) -> list[DatasetSummaryOut]:
        rows = await self.session.execute(
            _dataset_query.where(or_(Dataset.owner_id == user.id, Dataset.shared)).order_by(
                Dataset.created_at.desc(), Dataset.name
            )
        )
        return [_dataset_summary(r) for r in rows]

    async def _for_edit(self, user: CurrentUser, dataset_id: UUID) -> Dataset:
        # the row lock serialises writers, so positions stay unique and the case limit holds
        dataset = await self.session.scalar(
            select(Dataset).where(Dataset.id == dataset_id).with_for_update()
        )
        return require_edit(dataset, user.id)

    async def _case(self, dataset_id: UUID, case_id: UUID) -> DatasetCase:
        # filtering by dataset_id keeps a case of another dataset unreachable (404)
        row = await self.session.scalar(
            select(DatasetCase).where(
                DatasetCase.id == case_id, DatasetCase.dataset_id == dataset_id
            )
        )
        if row is None:
            raise NotFound("Не найдено")
        return row

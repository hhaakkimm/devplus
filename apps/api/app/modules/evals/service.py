from uuid import UUID

from sqlalchemy import Row, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.service import CurrentUser
from app.modules.evals.access import require_edit, require_view
from app.modules.evals.models import Prompt, PromptVersion, users
from app.modules.evals.schemas import (
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
        name = source.name[: MAX_NAME - len(COPY_SUFFIX)] + COPY_SUFFIX
        latest = VersionIn.model_validate(source.versions[-1].model_dump())
        return await self.create(user, name, latest)

    async def get_version(self, user: CurrentUser, version_id: UUID) -> VersionOut:
        version = await self.session.get(PromptVersion, version_id)
        prompt = await self.session.get(Prompt, version.prompt_id) if version else None
        require_view(prompt, user.id)
        assert version is not None
        return VersionOut.model_validate(version)

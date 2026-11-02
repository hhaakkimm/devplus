"""Code review tasks as folders: `content/<NN-module>/tasks/<slug>/`.

`task.yaml` (hidden part) and `reference_review.yaml` are read by the API only; `task.mdx` is the
statement; `code/` holds the files the student reviews. A folder without `task.yaml` is not a task,
and the Trainer loader skips these folders (it reads only flat `NN-slug.yaml` files)."""

import re
from functools import cache
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

FALSE_FINDINGS = "Ложные замечания"
PRIORITIES = "Приоритеты и вердикт"
MAX_CODE_BYTES = 60 * 1024  # the upper bound of the judge's input

_MODULE = re.compile(r"(\d{2})-([a-z0-9-]+)")
_SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)(?:\r?\n---\r?\n|\r?\n---\Z)", re.DOTALL)

Slug = Annotated[str, StringConstraints(pattern=_SLUG)]
Verdict = Literal["approve", "request_changes"]


class TaskFileError(Exception):
    """A task file that cannot be used; the message starts with the file."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Located(_Model):
    file: str
    lines: tuple[int, int]

    @field_validator("lines")
    @classmethod
    def check_lines(cls, v: tuple[int, int]) -> tuple[int, int]:
        if not 1 <= v[0] <= v[1]:
            raise ValueError("lines: нужно 1 <= начало <= конец")
        return v


class Issue(_Located):
    id: Slug
    critical: bool = False
    weight: float = Field(gt=0, le=100)  # the bounds of a rubric section
    description: str  # the judge and the student, after sending
    notes: str  # the judge only


class Trap(_Located):
    why_fine: str


class Section(_Model):
    name: str
    description: str
    weight: float = Field(gt=0, le=100)


class ReviewComment(_Model):
    file: str
    line_start: int = Field(ge=1)
    line_end: int
    text: str

    @model_validator(mode="after")
    def check_range(self) -> "ReviewComment":
        if self.line_end < self.line_start:
            raise ValueError("line_end меньше line_start")
        return self


class _Reference(_Model):
    verdict: Verdict
    comments: list[ReviewComment]


class TaskSpec(_Model):
    module: str
    slug: str
    title: str
    difficulty: Literal["easy", "medium", "hard"]
    order: int
    estimate_min: int = Field(ge=1)
    threshold: float = Field(gt=0, le=1)
    issues: list[Issue] = Field(min_length=1, max_length=7)
    traps: list[Trap] = Field(default=[], max_length=3)
    general_rubric: list[Section]
    expected_verdict: Verdict
    statement: str
    files: dict[str, str]  # by the path relative to `code/`, with `/`
    reference: list[ReviewComment]
    reference_verdict: str

    @property
    def key(self) -> str:
        return f"{self.module}/{self.slug}"

    @model_validator(mode="after")
    def check_task(self) -> "TaskSpec":
        # ponytail: the rubric (issues + 2) cannot exceed 10 sections, as issues are at most 7
        ids = [i.id for i in self.issues]
        if len(set(ids)) != len(ids):
            raise ValueError("id проблем повторяются")
        if sorted(s.name for s in self.general_rubric) != sorted([FALSE_FINDINGS, PRIORITIES]):
            raise ValueError(f"general_rubric: ровно разделы «{FALSE_FINDINGS}» и «{PRIORITIES}»")
        if self.expected_verdict == "request_changes" and not any(i.critical for i in self.issues):
            raise ValueError("при request_changes нужна хотя бы одна critical проблема")
        for place in (*self.issues, *self.traps):
            if place.file not in self.files:
                raise ValueError(f"файла {place.file} нет в code/")
            if place.lines[1] > len(self.files[place.file].splitlines()):
                raise ValueError(f"{place.file}: строки {list(place.lines)} вне файла")
        return self


def _mapping(path: Path, text: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise TaskFileError(path, str(e)) from e
    if not isinstance(data, dict):
        raise TaskFileError(path, "ожидается словарь с полями")
    return data


def _problems(e: ValidationError) -> str:
    return "; ".join(
        (".".join(map(str, p["loc"])) + ": " if p["loc"] else "") + p["msg"] for p in e.errors()
    )


def _read(path: Path) -> str:
    if not path.is_file():
        raise TaskFileError(path, "нет файла")
    try:
        return path.read_text("utf-8")
    except UnicodeDecodeError as e:
        raise TaskFileError(path, "файл не в UTF-8") from e


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def _check_reference(path: Path, task: TaskSpec) -> None:
    """The machine check: it covers every issue, touches no trap, agrees on the verdict."""
    spans = [(c.file, (c.line_start, c.line_end)) for c in task.reference]
    for file, _ in spans:
        if file not in task.files:
            raise TaskFileError(path, f"файла {file} нет в code/")
    if task.reference_verdict != task.expected_verdict:
        raise TaskFileError(
            path, f"вердикт {task.reference_verdict}, ожидается {task.expected_verdict}"
        )
    for trap in task.traps:
        if any(f == trap.file and _overlap(s, trap.lines) for f, s in spans):
            raise TaskFileError(path, f"замечание эталона задевает ловушку в {trap.file}")
    for issue in task.issues:
        if not any(f == issue.file and _overlap(s, issue.lines) for f, s in spans):
            raise TaskFileError(path, f"эталон не покрывает проблему {issue.id}")


def _load(module: str, slug: str, folder: Path) -> TaskSpec:
    yaml_path, mdx_path, ref_path = (
        folder / "task.yaml",
        folder / "task.mdx",
        folder / "reference_review.yaml",
    )
    if re.fullmatch(_SLUG, slug) is None:
        raise TaskFileError(folder, "имя папки задачи: латиница, цифры и дефисы")
    data = _mapping(yaml_path, _read(yaml_path))
    mdx = _read(mdx_path)
    found = _FRONTMATTER.match(mdx)
    statement = (mdx[found.end() :] if found else mdx).strip()
    if not statement:
        raise TaskFileError(mdx_path, "пустое условие")
    try:
        reference = _Reference.model_validate(_mapping(ref_path, _read(ref_path)))
    except ValidationError as e:
        raise TaskFileError(ref_path, _problems(e)) from e
    code = folder / "code"
    paths = sorted(p for p in code.rglob("*") if p.is_file()) if code.is_dir() else []
    if sum(p.stat().st_size for p in paths) > MAX_CODE_BYTES:
        raise TaskFileError(yaml_path, f"code/ больше {MAX_CODE_BYTES // 1024} КБ")
    files = {p.relative_to(code).as_posix(): _read(p) for p in paths}
    try:
        task = TaskSpec.model_validate(
            data
            | {
                "module": module,
                "slug": slug,
                "statement": statement,
                "files": files,
                "reference": reference.comments,
                "reference_verdict": reference.verdict,
            }
        )
    except ValidationError as e:
        raise TaskFileError(yaml_path, _problems(e)) from e
    _check_reference(ref_path, task)
    return task


def load_tasks(content_dir: Path) -> list[TaskSpec]:
    """Every task under `content_dir`, ordered by the module number, then `order`."""
    found: list[tuple[int, TaskSpec]] = []
    for module_dir in sorted(content_dir.iterdir()):
        named = _MODULE.fullmatch(module_dir.name)
        folder = module_dir / "tasks"
        if named is None or not folder.is_dir():
            continue
        for task_dir in sorted(folder.iterdir()):
            if (task_dir / "task.yaml").is_file():
                task = _load(named[2], task_dir.name, task_dir)
                found.append((int(named[1]), task))
    return [t for _, t in sorted(found, key=lambda f: (f[0], f[1].order, f[1].slug))]


# shortcut: tasks are read once per process, so an edited task needs an API restart; reload on
# change if authors start editing against a running API
@cache
def cached_tasks(content_dir: Path) -> tuple[TaskSpec, ...]:
    return tuple(load_tasks(content_dir))

"""Trainer tasks as files: `content/<NN-module>/tasks/<NN-task>.yaml` and the `.mdx` beside it.

The YAML (model, graders, hidden cases) is read by the API only; the MDX gives the title and
summary in its frontmatter and is rendered by the web."""

import re
from functools import cache
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import ConfigDict, Field, StringConstraints, ValidationError, model_validator

from app.modules.evals.service import EFFORTS, MODELS, CaseIn, GradersIn

_MODULE = re.compile(r"\d{2}-([a-z0-9-]+)")
_TASK = re.compile(r"\d{2}-([a-z0-9-]+)\.(?:yaml|mdx)")
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)(?:\r?\n---\r?\n|\r?\n---\Z)", re.DOTALL)

# what a `{{variable}}` of a template can be called
Variable = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]


class TaskFileError(Exception):
    """A task file that cannot be used; the message starts with the file."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")


class TaskSpec(GradersIn):
    model_config = ConfigDict(extra="forbid", frozen=True)

    module: str
    slug: str
    title: str
    summary: str
    model: Literal[*MODELS]  # type: ignore[valid-type]
    effort: Literal[*EFFORTS]  # type: ignore[valid-type]
    max_tokens: int = Field(ge=1, le=16000)  # the bounds of a prompt version
    variables: list[Variable] = Field(min_length=1)
    pass_threshold: float = Field(gt=0, le=1)  # the share of cases that must pass
    cases: list[CaseIn] = Field(min_length=1)

    @model_validator(mode="after")
    def check_task(self) -> "TaskSpec":
        if not self.graders:
            raise ValueError("нужен хотя бы один оценщик")
        # else every attempt would be refused with "не хватает переменных", whatever the prompt
        for i, case in enumerate(self.cases, 1):
            if missing := set(self.variables) - case.variables.keys():
                raise ValueError(f"в кейсе {i} нет переменных: {', '.join(sorted(missing))}")
        return self


def _mapping(path: Path, text: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise TaskFileError(path, str(e)) from e
    if not isinstance(data, dict):
        raise TaskFileError(path, "ожидается словарь с полями")
    return data


def _frontmatter(path: Path) -> dict[str, Any]:
    found = _FRONTMATTER.match(path.read_text("utf-8"))
    if found is None:
        raise TaskFileError(path, "нет frontmatter с title и summary")
    return _mapping(path, found[1])


def _problems(e: ValidationError) -> str:
    return "; ".join(
        (".".join(map(str, p["loc"])) + ": " if p["loc"] else "") + p["msg"] for p in e.errors()
    )


def _load(module: str, slug: str, yaml_path: Path, mdx_path: Path) -> TaskSpec:
    meta = _frontmatter(mdx_path)
    title, summary = meta.get("title"), meta.get("summary")
    if not isinstance(title, str) or not isinstance(summary, str):
        raise TaskFileError(mdx_path, "во frontmatter нужны title и summary")
    data = _mapping(yaml_path, yaml_path.read_text("utf-8"))
    try:
        return TaskSpec.model_validate(
            data | {"module": module, "slug": slug, "title": title, "summary": summary}
        )
    except ValidationError as e:
        raise TaskFileError(yaml_path, _problems(e)) from e


def load_tasks(content_dir: Path) -> list[TaskSpec]:
    """Every task under `content_dir`, ordered by the numeric prefixes of module and task."""
    tasks: list[TaskSpec] = []
    seen: set[tuple[str, str]] = set()
    for module_dir in sorted(content_dir.iterdir()):
        named = _MODULE.fullmatch(module_dir.name)
        folder = module_dir / "tasks"
        if named is None or not folder.is_dir():
            continue
        module = named[1]
        for stem in sorted({p.stem for p in folder.iterdir() if _TASK.fullmatch(p.name)}):
            yaml_path, mdx_path = folder / f"{stem}.yaml", folder / f"{stem}.mdx"
            for path, other in ((yaml_path, mdx_path), (mdx_path, yaml_path)):
                if path.exists() and not other.exists():
                    raise TaskFileError(path, f"нет парного файла {other.name}")
            slug = stem.split("-", 1)[1]
            if (module, slug) in seen:
                raise TaskFileError(yaml_path, f"задача {module}/{slug} уже есть")
            seen.add((module, slug))
            tasks.append(_load(module, slug, yaml_path, mdx_path))
    return tasks


# shortcut: tasks are read once per process, so an edited task needs an API restart; reload on
# change if authors start editing against a running API
@cache
def cached_tasks(content_dir: Path) -> tuple[TaskSpec, ...]:
    return tuple(load_tasks(content_dir))

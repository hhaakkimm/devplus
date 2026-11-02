"""Simulator tasks as files: `content/<NN-module>/simulator/<NN-task>.yaml` and its `.mdx`.

The YAML (scale, scenarios, review, reference graph) is read by the API only; the MDX gives the
title and summary in its frontmatter, and its body is the statement."""

import re
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.modules.evals.service import RubricSection
from app.modules.simulator.engine.graph import Graph
from app.modules.simulator.engine.scenarios import Scenario

_MODULE = re.compile(r"\d{2}-([a-z0-9-]+)")
_TASK = re.compile(r"\d{2}-([a-z0-9-]+)\.(?:yaml|mdx)")
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)(?:\r?\n---\r?\n|\r?\n---\Z)", re.DOTALL)


class SimTaskFileError(Exception):
    """A task file that cannot be used; the message starts with the file."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Scale(_Model):
    peak_rps: float = Field(gt=0, le=10_000_000)
    read_ratio: float = Field(ge=0, le=1)


class ReviewSpec(_Model):
    threshold: float = Field(gt=0, le=1)
    rubric: list[RubricSection] = Field(min_length=1, max_length=10)
    reference: str = Field(min_length=1)  # the judge only


class SimTask(_Model):
    module: str
    slug: str
    title: str
    summary: str
    statement: str  # the MDX body without frontmatter
    scale: Scale
    scenarios: list[Scenario]
    review: ReviewSpec
    reference_graph: Graph  # tests only

    @model_validator(mode="after")
    def check_task(self) -> "SimTask":
        if not any(s.visible for s in self.scenarios):
            raise ValueError("нужен хотя бы один открытый сценарий")
        if all(s.visible for s in self.scenarios):
            raise ValueError("нужен хотя бы один скрытый сценарий")
        ids = [s.id for s in self.scenarios]
        if len(set(ids)) != len(ids):
            raise ValueError("id сценариев повторяются")
        return self


def _read(path: Path) -> str:
    try:
        return path.read_text("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise SimTaskFileError(path, f"не читается: {e}") from e


def _mapping(path: Path, text: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise SimTaskFileError(path, str(e)) from e
    if not isinstance(data, dict):
        raise SimTaskFileError(path, "ожидается словарь с полями")
    return data


def _problems(e: ValidationError) -> str:
    return "; ".join(
        (".".join(map(str, p["loc"])) + ": " if p["loc"] else "") + p["msg"] for p in e.errors()
    )


def _load(module: str, slug: str, yaml_path: Path, mdx_path: Path) -> SimTask:
    mdx = _read(mdx_path)
    found = _FRONTMATTER.match(mdx)
    if found is None:
        raise SimTaskFileError(mdx_path, "нет frontmatter с title и summary")
    meta = _mapping(mdx_path, found[1])
    title, summary = meta.get("title"), meta.get("summary")
    if not isinstance(title, str) or not isinstance(summary, str):
        raise SimTaskFileError(mdx_path, "во frontmatter нужны title и summary")
    statement = mdx[found.end() :].strip()
    if not statement:
        raise SimTaskFileError(mdx_path, "пустое условие")
    data = _mapping(yaml_path, _read(yaml_path))
    try:
        return SimTask.model_validate(
            data
            | {
                "module": module,
                "slug": slug,
                "title": title,
                "summary": summary,
                "statement": statement,
            }
        )
    except ValidationError as e:
        raise SimTaskFileError(yaml_path, _problems(e)) from e


def load_sim_tasks(content_dir: Path) -> list[SimTask]:
    """Every task under `content_dir`, ordered by the numeric prefixes of module and task."""
    tasks: list[SimTask] = []
    seen: set[tuple[str, str]] = set()
    for module_dir in sorted(content_dir.iterdir()):
        named = _MODULE.fullmatch(module_dir.name)
        folder = module_dir / "simulator"
        if named is None or not folder.is_dir():
            continue
        module = named[1]
        for stem in sorted({p.stem for p in folder.iterdir() if _TASK.fullmatch(p.name)}):
            yaml_path, mdx_path = folder / f"{stem}.yaml", folder / f"{stem}.mdx"
            for path, other in ((yaml_path, mdx_path), (mdx_path, yaml_path)):
                if path.exists() and not other.exists():
                    raise SimTaskFileError(path, f"нет парного файла {other.name}")
            slug = stem.split("-", 1)[1]
            if (module, slug) in seen:
                raise SimTaskFileError(yaml_path, f"задача {module}/{slug} уже есть")
            seen.add((module, slug))
            tasks.append(_load(module, slug, yaml_path, mdx_path))
    return tasks


# shortcut: задачи кэшируются до рестарта API, перезагрузка без рестарта не нужна команде
@cache
def cached_sim_tasks(content_dir: Path) -> tuple[SimTask, ...]:
    return tuple(load_sim_tasks(content_dir))

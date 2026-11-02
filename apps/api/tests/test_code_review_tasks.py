import re
import shutil
from pathlib import Path

import pytest
import yaml

from app.modules.code_review.tasks import FALSE_FINDINGS, PRIORITIES, TaskFileError, load_tasks
from app.modules.trainer import tasks as trainer_tasks

FIXTURES = Path(__file__).parent / "fixtures" / "code_review"
REAL = Path(__file__).parents[3] / "content"
DEMO = FIXTURES / "00-start" / "tasks" / "demo"


def put(root: Path, *, task=None, reference=None, mdx=True, files=None, ref=True) -> Path:
    """Copy the fixture task into `root`, then change its parts."""
    folder = root / "00-start" / "tasks" / "demo"
    shutil.copytree(DEMO, folder)
    for name, data in (("task.yaml", task), ("reference_review.yaml", reference)):
        if data is not None:
            text = yaml.safe_load((folder / name).read_text("utf-8"))
            (folder / name).write_text(yaml.safe_dump(data(text) or text), "utf-8")
    if not mdx:
        (folder / "task.mdx").unlink()
    if not ref:
        (folder / "reference_review.yaml").unlink()
    for name, text in (files or {}).items():
        (folder / "code" / name).write_text(text, "utf-8")
    return root


def drop(key):
    def f(d):
        del d[key]

    return f


def issue_extra(**kw):
    def f(d):
        d["issues"].append(
            {
                "id": "x",
                "file": "store.py",
                "lines": [1, 1],
                "weight": 1,
                "description": "d",
                "notes": "n",
            }
            | kw
        )

    return f


def set_(path, value):
    def f(d):
        *keys, last = path
        for k in keys:
            d = d[k]
        d[last] = value

    return f


def many(n):
    def f(d):
        d["issues"] = [
            {
                "id": f"i{i}",
                "file": "store.py",
                "lines": [1, 1],
                "weight": 1,
                "description": "d",
                "notes": "n",
            }
            | ({"critical": True} if i == 0 else {})
            for i in range(n)
        ]

    return f


def traps(n):
    def f(d):
        d["traps"] = [{"file": "store.py", "lines": [1, 1], "why_fine": "w"}] * n

    return f


def reference_drop_first(d):
    d["comments"].pop(0)


def reference_hits_trap(d):
    d["comments"].append({"file": "worker.py", "line_start": 29, "line_end": 29, "text": "t"})


def test_loads_fixture_task():
    [task] = load_tasks(FIXTURES)
    assert (task.key, task.module, task.slug) == ("start/demo", "start", "demo")
    assert (task.difficulty, task.order, task.estimate_min, task.threshold) == (
        "medium",
        10,
        15,
        0.7,
    )
    assert [i.id for i in task.issues] == ["race-on-claim", "sql-format"]
    assert task.issues[0].lines == (18, 22) and task.issues[0].critical
    assert not task.issues[1].critical and "СЕКРЕТ-NOTES" in task.issues[0].notes
    assert [t.file for t in task.traps] == ["worker.py"]
    assert "СЕКРЕТ-WHY" in task.traps[0].why_fine
    assert [s.name for s in task.general_rubric] == [FALSE_FINDINGS, PRIORITIES]
    assert task.expected_verdict == "request_changes"
    assert set(task.files) == {"worker.py", "store.py"}
    assert task.files["store.py"].startswith('"""Job store')
    assert task.statement.startswith("## Контекст") and "title:" not in task.statement
    assert task.reference_verdict == "request_changes"
    assert [(c.file, c.line_start, c.line_end) for c in task.reference] == [
        ("worker.py", 18, 22),
        ("store.py", 16, 16),
    ]


def test_files_keys_are_relative_to_code(tmp_path):
    put(tmp_path)
    sub = tmp_path / "00-start" / "tasks" / "demo" / "code" / "pkg"
    sub.mkdir()
    (sub / "a.py").write_text("x = 1\n", "utf-8")
    [task] = load_tasks(tmp_path)
    assert "pkg/a.py" in task.files


def test_orders_by_module_number_then_order(tmp_path):
    put(tmp_path)
    other = tmp_path / "00-start" / "tasks" / "first"
    shutil.copytree(DEMO, other)
    data = yaml.safe_load((other / "task.yaml").read_text("utf-8"))
    (other / "task.yaml").write_text(yaml.safe_dump(data | {"order": 5}), "utf-8")
    assert [t.slug for t in load_tasks(tmp_path)] == ["first", "demo"]


def test_folder_without_task_yaml_is_skipped(tmp_path):
    put(tmp_path)
    (tmp_path / "00-start" / "tasks" / "notes").mkdir()
    assert [t.slug for t in load_tasks(tmp_path)] == ["demo"]


@pytest.mark.parametrize(
    ("kwargs", "bad", "why"),
    [
        pytest.param({"task": many(8)}, "task.yaml", "at most 7", id="8 issues"),
        pytest.param({"task": traps(4)}, "task.yaml", "at most 3", id="4 traps"),
        pytest.param(
            {"task": set_(["issues", 0, "lines"], [18, 99])}, "task.yaml", "вне файла", id="range"
        ),
        pytest.param(
            {"task": set_(["issues", 0, "lines"], [22, 18])},
            "task.yaml",
            "1 <= начало",
            id="reversed",
        ),
        pytest.param(
            {"task": set_(["issues", 0, "lines"], [0, 3])},
            "task.yaml",
            "1 <= начало",
            id="from zero",
        ),
        pytest.param(
            {"task": set_(["issues", 0, "file"], "nope.py")},
            "task.yaml",
            "нет в code/",
            id="no file",
        ),
        pytest.param(
            {"task": set_(["traps", 0, "file"], "nope.py")},
            "task.yaml",
            "нет в code/",
            id="trap file",
        ),
        pytest.param(
            {"task": issue_extra(id="sql-format")}, "task.yaml", "повторяются", id="duplicate id"
        ),
        pytest.param(
            {"task": set_(["issues", 0, "id"], "Not A Slug")},
            "task.yaml",
            "issues.0.id: String should match",
            id="bad id",
        ),
        pytest.param(
            {"task": set_(["issues", 0, "critical"], False)},
            "task.yaml",
            "critical",
            id="no critical",
        ),
        pytest.param(
            {"task": set_(["general_rubric", 0, "name"], "Чужое")},
            "task.yaml",
            "ровно",
            id="rubric",
        ),
        pytest.param(
            {"task": drop("difficulty")},
            "task.yaml",
            "difficulty: Field required",
            id="no difficulty",
        ),
        pytest.param({"task": drop("order")}, "task.yaml", "order: Field required", id="no order"),
        pytest.param(
            {"files": {"big.py": "x" * (60 * 1024)}}, "task.yaml", "больше 60", id="code over 60 KB"
        ),
        pytest.param({"mdx": False}, "task.mdx", "нет файла", id="no mdx"),
        pytest.param({"ref": False}, "reference_review.yaml", "нет файла", id="no reference"),
        pytest.param(
            {"reference": reference_drop_first},
            "reference_review.yaml",
            "не покрывает проблему race-on-claim",
            id="uncovered",
        ),
        pytest.param(
            {"reference": reference_hits_trap},
            "reference_review.yaml",
            "задевает ловушку",
            id="trap hit",
        ),
        pytest.param(
            {"reference": set_(["verdict"], "approve")},
            "reference_review.yaml",
            "вердикт approve",
            id="verdict",
        ),
    ],
)
def test_rejects(tmp_path, kwargs, bad, why):
    put(tmp_path, **kwargs)
    with pytest.raises(TaskFileError, match=re.escape(bad) + ".*" + re.escape(why)):
        load_tasks(tmp_path)


def test_slug_dirs_next_to_trainer_files_are_ignored_by_trainer(tmp_path):
    put(tmp_path)
    (tmp_path / "00-start" / "tasks" / "01-flat.yaml").write_text("x: 1\n", "utf-8")
    (tmp_path / "00-start" / "tasks" / "01-flat.mdx").write_text("---\ntitle: T\nsummary: S\n---\n")
    # the flat file is invalid for the trainer: it must fail on that file only, never on demo/
    with pytest.raises(trainer_tasks.TaskFileError, match=r"01-flat\.yaml"):
        trainer_tasks.load_tasks(tmp_path)
    (tmp_path / "00-start" / "tasks" / "01-flat.yaml").unlink()
    (tmp_path / "00-start" / "tasks" / "01-flat.mdx").unlink()
    assert trainer_tasks.load_tasks(tmp_path) == []


def test_real_content_loads():
    load_tasks(REAL)

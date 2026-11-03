from pathlib import Path

import pytest
import yaml

from app.modules.simulator.engine.graph import Graph, structural_errors
from app.modules.simulator.engine.lint import lint
from app.modules.simulator.engine.scenarios import run_scenario
from app.modules.simulator.tasks import SimTaskFileError, cached_sim_tasks, load_sim_tasks

FIXTURES = Path(__file__).parent / "fixtures" / "content_sim"
REAL = Path(__file__).parents[3] / "content"
TASK = FIXTURES / "10-system-design" / "simulator" / "01-url-shortener"
RUBRIC = ["Требования и допущения", "Оценка нагрузки", "Архитектура", "Компромиссы"]
NAIVE = Graph.model_validate(
    {
        "nodes": [
            {"id": "user", "type": "User"},
            {"id": "server", "type": "Server"},
            {"id": "db", "type": "Database"},
        ],
        "edges": [{"source": "user", "target": "server"}, {"source": "server", "target": "db"}],
    }
)


def put(root: Path, change=None, *, name="01-url-shortener", mdx=None, pair=True) -> Path:
    """Copy the fixture task into `root` as `name`, then change its YAML or MDX."""
    folder = root / "10-system-design" / "simulator"
    folder.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load(TASK.with_suffix(".yaml").read_text("utf-8"))
    if change is not None:
        change(data)
    (folder / f"{name}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), "utf-8")
    if pair:
        text = mdx if mdx is not None else TASK.with_suffix(".mdx").read_text("utf-8")
        (folder / f"{name}.mdx").write_text(text, "utf-8")
    return folder


def hide_all(d):
    for s in d["scenarios"]:
        s["visible"] = False


def show_all(d):
    for s in d["scenarios"]:
        s["visible"] = True


def repeat_id(d):
    d["scenarios"][1]["id"] = "normal"


def test_load_reads_fixture():
    [task] = load_sim_tasks(FIXTURES)
    assert (task.module, task.slug) == ("system-design", "url-shortener")
    assert (task.title, task.summary) == (
        "Сокращатель ссылок",
        "Спроектируй сервис коротких ссылок, который держит пик чтений.",
    )
    assert task.statement.startswith("## Контекст") and "title:" not in task.statement
    assert task.statement.endswith("сценарии нагрузки и отказов.")
    assert (task.scale.peak_rps, task.scale.read_ratio) == (1000, 0.9)
    assert [(s.id, s.visible) for s in task.scenarios] == [
        ("normal", True),
        ("spike", True),
        ("db-down", False),
    ]
    assert task.scenarios[2].failure is not None
    assert task.scenarios[2].failure.type == "Database"
    assert task.review.threshold == 0.7
    assert [s.name for s in task.review.rubric] == RUBRIC
    assert "СЕКРЕТ-ЭТАЛОН" in task.review.reference
    assert [n.type for n in task.reference_graph.nodes] == [
        "User",
        "LoadBalancer",
        "Server",
        "Cache",
        "Database",
    ]


@pytest.mark.parametrize(
    ("change", "mdx", "pair", "bad"),
    [
        pytest.param(None, "---\ntitle: [\n---\n## Контекст\n", True, "mdx", id="broken meta"),
        pytest.param(None, "## Контекст\n", True, "mdx", id="no frontmatter"),
        pytest.param(None, "---\ntitle: T\n---\n## Контекст\n", True, "mdx", id="no summary"),
        pytest.param(None, "---\ntitle: T\nsummary: S\n---\n", True, "mdx", id="empty statement"),
        pytest.param(None, None, False, "yaml", id="yaml without mdx"),
        pytest.param(lambda d: d.update(extra=1), None, True, "yaml", id="unknown field"),
        pytest.param(
            lambda d: d["scenarios"][0].update(max_latency=1), None, True, "yaml", id="typo"
        ),
        pytest.param(
            lambda d: d["review"].update(threshold=0), None, True, "yaml", id="threshold zero"
        ),
        pytest.param(lambda d: d["review"].update(reference=""), None, True, "yaml", id="no ref"),
        pytest.param(lambda d: d["scale"].update(peak_rps=0), None, True, "yaml", id="no load"),
        pytest.param(hide_all, None, True, "yaml", id="no visible scenario"),
        pytest.param(show_all, None, True, "yaml", id="no hidden scenario"),
        pytest.param(repeat_id, None, True, "yaml", id="repeated scenario id"),
        pytest.param(
            lambda d: d["reference_graph"]["nodes"][2]["params"].update(replicas=0),
            None,
            True,
            "yaml",
            id="bad graph",
        ),
        pytest.param(lambda d: d.pop("reference_graph"), None, True, "yaml", id="no graph"),
    ],
)
def test_bad_files_name_the_file(tmp_path, change, mdx, pair, bad):
    put(tmp_path, change, mdx=mdx, pair=pair)
    with pytest.raises(SimTaskFileError, match=rf"01-url-shortener\.{bad}"):
        load_sim_tasks(tmp_path)


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(b"scale: [", id="broken yaml"),
        pytest.param(b"- a\n- b\n", id="not a mapping"),
        pytest.param(b"\xff\xfe", id="not utf-8"),
    ],
)
def test_unreadable_yaml_names_the_file(tmp_path, raw):
    folder = put(tmp_path)
    (folder / "01-url-shortener.yaml").write_bytes(raw)
    with pytest.raises(SimTaskFileError, match=r"01-url-shortener\.yaml"):
        load_sim_tasks(tmp_path)


def test_mdx_without_yaml_names_the_file(tmp_path):
    folder = put(tmp_path)
    (folder / "01-url-shortener.yaml").unlink()
    with pytest.raises(SimTaskFileError, match=r"01-url-shortener\.mdx"):
        load_sim_tasks(tmp_path)


def test_repeated_slug_names_the_file(tmp_path):
    put(tmp_path)
    put(tmp_path, name="02-url-shortener")
    with pytest.raises(SimTaskFileError, match=r"02-url-shortener\.yaml"):
        load_sim_tasks(tmp_path)


def test_orders_by_prefix_and_ignores_other_files(tmp_path):
    folder = put(tmp_path, name="10-last")
    put(tmp_path, name="02-first")
    (folder / "notes.txt").write_text("x")
    # trainer tasks and lessons of the module are not simulator tasks
    (tmp_path / "10-system-design" / "tasks").mkdir()
    (tmp_path / "10-system-design" / "tasks" / "01-x.yaml").write_text("model: [")
    (tmp_path / "10-system-design" / "01-lesson.mdx").write_text("---\ntitle: T\n---\n")
    (tmp_path / "misc" / "simulator").mkdir(parents=True)
    assert [t.slug for t in load_sim_tasks(tmp_path)] == ["first", "last"]


def test_cached_sim_tasks_reads_a_path_once(tmp_path):
    folder = put(tmp_path)
    first = cached_sim_tasks(tmp_path)
    (folder / "01-url-shortener.yaml").write_text("scale: [")
    assert cached_sim_tasks(tmp_path) is first


@pytest.mark.parametrize("root", [FIXTURES, REAL], ids=["fixture", "real"])
def test_reference_passes_everything(root):
    tasks = load_sim_tasks(root)
    assert tasks
    for t in tasks:
        g = t.reference_graph
        assert structural_errors(g) == [], t.slug
        findings = lint(g, t.scale.read_ratio)
        assert not [f for f in findings if f.severity == "critical"], t.slug
        # the canonical edge → balancer → server → cache → database chain is not "too deep"
        assert "DEEP_SYNC_CHAIN" not in [f.code for f in findings], t.slug
        for s in t.scenarios:
            r = run_scenario(g, t.scale.peak_rps, t.scale.read_ratio, s)
            assert r.passed, (t.slug, s.id, r.explanation)
            # the reference never drops messages at a queue's door, even at ×10
            assert all(m.rho <= 1 for m in r.nodes.values() if m.type == "Queue"), (t.slug, s.id)


def test_real_content_naive_graph_fails():
    for t in load_sim_tasks(REAL):
        runs = [run_scenario(NAIVE, t.scale.peak_rps, t.scale.read_ratio, s) for s in t.scenarios]
        assert not all(r.passed for r in runs), t.slug


def test_real_content_has_the_agreed_shape():
    tasks = load_sim_tasks(REAL)
    assert [(t.module, t.slug, t.scale.peak_rps, t.scale.read_ratio) for t in tasks] == [
        ("system-design", "url-shortener", 20000, 0.95),
        ("system-design", "chat", 8000, 0.5),
        ("system-design", "news-feed", 15000, 0.9),
    ]
    for t in tasks:
        visible = [s.id for s in t.scenarios if s.visible]
        hidden = [s for s in t.scenarios if not s.visible]
        assert visible == ["normal", "spike"], t.slug
        assert 3 <= len(hidden) <= 4, t.slug
        failures = {(s.failure.type, s.failure.mode) for s in hidden if s.failure}
        assert {("Database", "replica"), ("Cache", "node")} <= failures, t.slug
        # a queue is a single node: failing it loses every message whatever the scheme
        assert all(s.failure is None or s.failure.type != "Queue" for s in t.scenarios), t.slug
        assert any(s.multiplier == 10 for s in hidden), t.slug
        assert t.review.threshold == 0.7
        assert [(s.name, s.weight) for s in t.review.rubric] == [(n, 1) for n in RUBRIC]
        assert 5 <= len(t.review.reference.strip().splitlines()) <= 10, t.slug
    for t in tasks[1:]:  # chat and news feed lose messages when a worker fails
        worker = [s for s in t.scenarios if s.failure and s.failure.type == "Worker"]
        assert [(s.failure.mode, s.visible) for s in worker if s.failure] == [("replica", False)]
        assert worker[0].max_message_loss < 1, t.slug

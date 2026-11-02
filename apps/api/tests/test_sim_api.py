import logging
from pathlib import Path

import pytest

from app.modules.simulator import service
from app.modules.simulator.engine.solver import EngineError
from app.modules.simulator.tasks import load_sim_tasks

REAL = Path(__file__).parents[3] / "content"
BASE = "/api/simulator"
TASK = f"{BASE}/tasks/system-design/url-shortener"
SIM_TASK = next(t for t in load_sim_tasks(REAL) if t.slug == "url-shortener")
HIDDEN = [s for s in SIM_TASK.scenarios if not s.visible]
VISIBLE = [s for s in SIM_TASK.scenarios if s.visible]
GOOD = SIM_TASK.reference_graph.model_dump()
USER = {"id": "user", "type": "User"}


def graph(nodes, edges):
    return {"graph": {"nodes": nodes, "edges": edges}}


def numbers(value) -> set[float]:
    """Every number in a parsed JSON document."""
    if isinstance(value, bool):
        return set()
    if isinstance(value, int | float):
        return {value}
    if isinstance(value, list):
        return set().union(*map(numbers, value)) if value else set()
    if isinstance(value, dict):
        return set().union(*map(numbers, value.values())) if value else set()
    return set()


def assert_nothing_hidden(body: str) -> None:
    for secret in ("reference", "rubric", "threshold", "Отказ базы", "review", "visible"):
        assert secret not in body
    for s in HIDDEN:
        assert s.title not in body
        assert s.id not in body  # ids like db-down name the failure


async def test_components_catalog(client, sign_in):
    await sign_in()
    res = await client.get(f"{BASE}/components")
    assert res.status_code == 200
    items = {c["type"]: c for c in res.json()}
    assert len(items) == 9
    assert items["Server"]["capacity_rps"] == 1000
    assert items["Server"]["latency_ms"] == 30
    assert items["User"]["capacity_rps"] is None
    assert items["Server"]["params"] == [
        {
            "key": "replicas",
            "label": "Копий",
            "kind": "int",
            "min": 1,
            "max": 100,
            "default": 1,
            "help": "Сколько копий сервера работает.",
        }
    ]
    assert "terminal_ok" not in items["Server"]


async def test_tasks_list(client, sign_in):
    await sign_in()
    res = await client.get(f"{BASE}/tasks")
    assert res.status_code == 200
    rows = res.json()
    assert [r["slug"] for r in rows] == ["url-shortener", "chat", "news-feed"]
    assert rows[0] == {
        "module": "system-design",
        "slug": "url-shortener",
        "title": SIM_TASK.title,
        "summary": SIM_TASK.summary,
        "solved": False,
    }
    assert_nothing_hidden(res.text)


async def test_task_hides_hidden_parts(client, sign_in):
    await sign_in()
    res = await client.get(TASK)
    assert res.status_code == 200
    body = res.text
    assert_nothing_hidden(body)
    data = res.json()
    assert data["scale"] == {"peak_rps": 20000, "read_ratio": 0.95}
    assert [s["id"] for s in data["scenarios"]] == [s.id for s in VISIBLE]
    assert set(data["scenarios"][0]) == {
        "id",
        "title",
        "multiplier",
        "duration_s",
        "failure",
        "max_latency_ms",
        "max_error_rate",
        "max_message_loss",
    }
    # a hidden target that no visible scenario or scale shares would show up as a number
    shown = numbers(data)
    for s in HIDDEN:
        visible_numbers = {x for v in VISIBLE for x in (v.max_latency_ms, v.max_error_rate)}
        for value in (s.max_latency_ms, s.max_error_rate, s.multiplier):
            if value not in visible_numbers | {1, 2}:
                assert value not in shown
        if s.failure:
            assert s.failure.type not in body


async def test_run_returns_visible_scenarios_only(client, sign_in):
    await sign_in()
    res = await client.post(f"{TASK}/run", json={"graph": GOOD})
    assert res.status_code == 200
    data = res.json()
    assert data["structural_errors"] == []
    assert [s["id"] for s in data["scenarios"]] == [s.id for s in VISIBLE]
    assert all(s["passed"] for s in data["scenarios"])
    first = data["scenarios"][0]
    assert "visible" not in first
    assert {n["id"] for n in first["nodes"]} == {n.id for n in SIM_TASK.reference_graph.nodes}
    assert set(first["nodes"][0]) == {
        "id",
        "type",
        "rps",
        "capacity_rps",
        "rho",
        "latency_ms",
        "errors_rps",
        "rejected_rps",
        "backlog",
        "message_loss",
    }
    assert data["findings"] == []  # the reference scheme has nothing to point out
    assert_nothing_hidden(res.text)


async def test_run_naive_graph_fails_with_explanation(client, sign_in):
    await sign_in()
    naive = graph(
        [USER, {"id": "server", "type": "Server"}, {"id": "db", "type": "Database"}],
        [{"source": "user", "target": "server"}, {"source": "server", "target": "db"}],
    )
    data = (await client.post(f"{TASK}/run", json=naive)).json()
    assert not data["scenarios"][0]["passed"]
    assert data["scenarios"][0]["explanation"]
    assert {f["code"] for f in data["findings"]} >= {"SINGLE_SERVER", "NO_CACHE_READ_HEAVY"}
    assert set(data["findings"][0]) == {"code", "severity", "message", "node_id"}


async def test_run_structural_errors_200(client, sign_in):
    await sign_in()
    # no path to a store from the server, and no User at all in the second graph
    dead_end = graph(
        [USER, {"id": "server", "type": "Server"}], [{"source": "user", "target": "server"}]
    )
    res = await client.post(f"{TASK}/run", json=dead_end)
    assert res.status_code == 200
    data = res.json()
    assert data["structural_errors"]
    assert data["scenarios"] == []
    assert data["findings"] == []
    no_user = await client.post(f"{TASK}/run", json=graph([], []))
    assert no_user.status_code == 200
    assert no_user.json()["structural_errors"] == ["Нужен ровно один узел User"]


@pytest.mark.parametrize(
    "body",
    [
        graph([USER, {"id": "x", "type": "Mainframe"}], []),
        graph([USER, {"id": "s", "type": "Server", "params": {"replicas": 0}}], []),
        graph([USER, {"id": "s", "type": "Server", "params": {"cores": 4}}], []),
        graph([{"id": f"n{i}", "type": "Server"} for i in range(51)], []),
        graph([USER, {"id": "a\x00b", "type": "Server"}], []),
        graph([USER, {"id": "a\n", "type": "Server"}], []),
        graph([USER], [{"source": "user", "target": "ghost"}]),
        {},
    ],
    ids=["type", "replicas", "param", "51-nodes", "nul-id", "newline-id", "dangling-edge", "empty"],
)
async def test_run_validation_422(client, sign_in, body):
    await sign_in()
    assert (await client.post(f"{TASK}/run", json=body)).status_code == 422


async def test_run_too_many_edges_422(client, sign_in):
    await sign_in()
    edges = [{"source": "user", "target": "s"}] * 101
    body = graph([USER, {"id": "s", "type": "Server"}], edges)
    assert (await client.post(f"{TASK}/run", json=body)).status_code == 422


async def test_unknown_task_404(client, sign_in):
    await sign_in()
    for path in ("system-design/nope", "nope/url-shortener"):
        assert (await client.get(f"{BASE}/tasks/{path}")).status_code == 404
        res = await client.post(f"{BASE}/tasks/{path}/run", json={"graph": GOOD})
        assert res.status_code == 404
        assert res.json() == {"detail": "Не найдено"}
    # a path-like slug never reaches the file system: no route, no task
    assert (await client.get(f"{BASE}/tasks/system-design/..%2Fx")).status_code == 404


async def test_requires_auth(client):
    for method, path in (
        ("get", f"{BASE}/components"),
        ("get", f"{BASE}/tasks"),
        ("get", TASK),
        ("post", f"{TASK}/run"),
    ):
        res = await getattr(client, method)(
            path, **({"json": {"graph": GOOD}} if method == "post" else {})
        )
        assert res.status_code == 401, path


async def test_engine_error_is_a_logged_500(client, sign_in, monkeypatch, caplog):
    await sign_in()

    def boom(*args, **kwargs):
        raise EngineError("Расчёт дал нечисловой результат")

    monkeypatch.setattr(service, "run_scenario", boom)
    with caplog.at_level(logging.ERROR):
        res = await client.post(f"{TASK}/run", json={"graph": GOOD})
    assert res.status_code == 500
    assert res.json() == {"detail": "Internal Server Error"}
    assert "нечисловой результат" in caplog.text

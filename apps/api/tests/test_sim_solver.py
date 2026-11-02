import math
from dataclasses import astuple
from itertools import pairwise

import pytest

from app.modules.simulator.engine.graph import Edge, Graph, Node
from app.modules.simulator.engine.solver import EngineError, Flow, solve


def approx(x: float) -> object:
    return pytest.approx(x, rel=1e-3)


def chain(*steps: str | tuple[str, dict[str, float]]) -> Graph:
    """User → steps in a line, sync edges with ratio 1; a step is a type or (type, params)."""
    nodes = [Node(id="user", type="User")]
    for step in steps:
        type_, params = (step, {}) if isinstance(step, str) else step
        nodes.append(
            Node(id="db" if type_ == "Database" else type_.lower(), type=type_, params=params)
        )
    return Graph(nodes=nodes, edges=[Edge(source=a.id, target=b.id) for a, b in pairwise(nodes)])


def all_finite(f: Flow) -> bool:
    values = [f.latency_ms, f.error_rate, f.rejected_rate, f.message_loss]
    values += [x for m in f.nodes.values() for x in astuple(m)[2:] if x is not None]
    return all(math.isfinite(x) for x in values)


def test_overloaded_server():
    f = solve(chain("Server", "Database"), 1500, 0.9, 60)
    assert f.nodes["server"].rho == approx(1.5) and f.nodes["server"].latency_ms == approx(600)
    assert f.nodes["server"].errors_rps == approx(500)
    assert f.nodes["db"].rps == approx(1000) and f.nodes["db"].latency_ms == approx(40)
    assert f.latency_ms == approx(640) and f.error_rate == approx(1 / 3)


def test_cache_cuts_db_load():
    g = chain(("Server", {"replicas": 2}), ("Cache", {"hit_ratio": 0.8}), "Database")
    f = solve(g, 1500, 0.9, 60)
    assert f.nodes["db"].rps == approx(420) and f.nodes["db"].latency_ms == approx(25.3165)
    assert f.latency_ms == approx(129.150) and f.error_rate == approx(0)


def test_read_replicas_split_reads():
    g = chain(("Server", {"replicas": 3}), ("Database", {"read_replicas": 2}))
    f = solve(g, 2400, 0.9, 60)
    assert f.nodes["db"].rho == approx(0.48) and f.error_rate == approx(0)
    assert f.nodes["db"].capacity_rps == approx(6000)

    f = solve(chain(("Server", {"replicas": 3}), "Database"), 2400, 0.9, 60)
    assert f.nodes["db"].rho == approx(1.2) and f.error_rate == approx(1 / 6)


def test_shards_split_reads_and_writes():
    g = chain(("Server", {"replicas": 3}), ("Database", {"shards": 2}))
    f = solve(g, 2400, 0.9, 60)
    assert f.nodes["db"].rho == approx(0.6) and f.error_rate == approx(0)


def test_queue_backlog_and_loss():
    g = chain("Server", ("Queue", {"max_size": 10000}), "Worker", "Database")
    f = solve(g, 800, 0, 60)
    assert f.latency_ms == approx(150) and f.error_rate == approx(0)
    assert f.message_loss == approx(1 / 6) and f.nodes["db"].rps == approx(500)
    assert f.nodes["queue"].backlog == approx(18000)
    assert f.nodes["queue"].message_loss == approx(1 / 6)
    assert f.nodes["worker"].errors_rps == 0


def test_queue_within_max_size_loses_nothing():
    g = chain("Server", ("Queue", {"max_size": 100_000}), "Worker", "Database")
    f = solve(g, 800, 0, 60)
    assert f.nodes["queue"].backlog == approx(18000) and f.message_loss == 0


def test_down_worker_queues_everything():
    g = chain("Server", ("Queue", {"max_size": 1000}), "Worker")
    f = solve(g, 400, 0, 60, down=frozenset({"worker"}))
    assert f.nodes["queue"].backlog == approx(24000) and f.nodes["worker"].errors_rps == 0
    assert f.message_loss == approx(23000 / 24000)


def test_worker_mixed_inputs_split_excess():
    # 10 000 rps straight into the Worker, 100 rps through the Queue; the worker takes 500
    g = Graph(
        nodes=[
            Node(id="user", type="User"),
            Node(id="server", type="Server", params={"replicas": 20}),
            Node(id="queue", type="Queue", params={"max_size": 1000}),
            Node(id="worker", type="Worker"),
        ],
        edges=[
            Edge(source="user", target="server"),
            Edge(source="server", target="worker"),
            Edge(source="server", target="queue", ratio=0.01),
            Edge(source="queue", target="worker"),
        ],
    )
    f = solve(g, 10000, 0, 60)
    excess = 10100 - 500
    assert f.nodes["worker"].errors_rps == approx(excess * 10000 / 10100)
    assert f.nodes["queue"].backlog == approx(excess * 100 / 10100 * 60)
    assert f.message_loss == approx((excess * 100 / 10100 * 60 - 1000) / (100 * 60))
    assert 0 < f.message_loss <= 1


def test_worker_without_queue_is_like_server():
    f = solve(chain("Worker"), 1000, 0.5, 60)
    # edges into a Worker are async, so its errors never reach the user
    assert f.nodes["worker"].errors_rps == approx(500) and f.error_rate == 0


def test_down_terminal_fails_everything():
    f = solve(chain("Server", "Database"), 1000, 0.9, 60, down=frozenset({"db"}))
    assert f.error_rate == approx(1.0)
    db = f.nodes["db"]
    assert db.capacity_rps == 0 and db.errors_rps == approx(1000) and db.rho >= 1
    assert all_finite(f)


def test_rate_limiter_rejects():
    g = chain(("RateLimiter", {"limit_rps": 1000}), ("Server", {"replicas": 2}), "Database")
    f = solve(g, 3000, 0.9, 60)
    assert f.rejected_rate == approx(2 / 3) and f.error_rate == approx(2 / 3)
    assert f.nodes["ratelimiter"].rejected_rps == approx(2000)
    assert f.nodes["server"].rps == approx(1000)


def test_more_replicas_never_more_errors():
    errors = [
        solve(chain(("Server", {"replicas": r}), "Database"), 3000, 0.9, 60).error_rate
        for r in range(1, 6)
    ]
    assert errors == sorted(errors, reverse=True)
    assert errors[0] > errors[-1]


def test_cache_never_raises_db_load():
    hits = [i / 10 for i in range(10)] + [0.99]
    loads = [
        solve(
            chain(("Server", {"replicas": 2}), ("Cache", {"hit_ratio": h}), "Database"),
            1500,
            0.9,
            60,
        )
        .nodes["db"]
        .rps
        for h in hits
    ]
    assert loads == sorted(loads, reverse=True)
    assert loads[0] > loads[-1]


def test_degenerate_flows_are_finite():
    g = Graph(
        nodes=[
            Node(id="user", type="User"),
            Node(id="server", type="Server"),
            Node(id="cache", type="Cache", params={"hit_ratio": 0.99}),
            Node(id="db", type="Database"),
            Node(id="idle", type="Database"),
        ],
        edges=[
            Edge(source="user", target="server"),
            Edge(source="server", target="cache"),
            Edge(source="cache", target="db"),
            Edge(source="server", target="idle", ratio=0),
        ],
    )
    f = solve(g, 500, 0.9, 60)
    assert all_finite(f) and f.error_rate == approx(0)
    idle = f.nodes["idle"]
    assert idle.rps == 0 and idle.rho == 0 and idle.errors_rps == 0 and idle.latency_ms == 20

    # nothing arrives anywhere: every node serves its whole (empty) flow at base latency
    f = solve(g, 0, 0.9, 60)
    assert all_finite(f) and f.error_rate == 0 and f.rejected_rate == 0
    assert {i: m.latency_ms for i, m in f.nodes.items()} == {
        "user": 0,
        "server": 30,
        "cache": 2,
        "db": 20,
        "idle": 20,
    }


def test_non_finite_numbers_are_engine_error():
    with pytest.raises(EngineError):
        solve(chain("Server", "Database"), math.inf, 0.9, 60)

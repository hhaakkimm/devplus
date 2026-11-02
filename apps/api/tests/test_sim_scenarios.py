import pytest
from pydantic import ValidationError

from app.modules.simulator.engine.graph import Edge, Graph, Node
from app.modules.simulator.engine.scenarios import Failure, Scenario, apply_failure, run_scenario
from app.modules.simulator.engine.solver import solve


def approx(x: float) -> object:
    return pytest.approx(x, rel=1e-3)


def node(id, type, **params):
    return Node(id=id, type=type, params=params)


def server_db(replicas=1, read_replicas=0, ratio=1.0):
    """User → Server → Database."""
    return Graph(
        nodes=[
            node("user", "User"),
            node("server", "Server", replicas=replicas),
            node("db", "Database", read_replicas=read_replicas),
        ],
        edges=[
            Edge(source="user", target="server"),
            Edge(source="server", target="db", ratio=ratio),
        ],
    )


def server_queue(replicas=1, max_size=1000):
    """User → Server → Queue → Worker, one worker copy (500 rps)."""
    return Graph(
        nodes=[
            node("user", "User"),
            node("server", "Server", replicas=replicas),
            node("queue", "Queue", max_size=max_size),
            node("worker", "Worker"),
        ],
        edges=[
            Edge(source="user", target="server"),
            Edge(source="server", target="queue"),
            Edge(source="queue", target="worker"),
        ],
    )


def scenario(**kw):
    base = dict(
        id="s",
        title="Сценарий",
        visible=True,
        multiplier=1,
        max_latency_ms=100_000,
        max_error_rate=1,
        max_message_loss=1,
    )
    return Scenario(**{**base, **kw})


def test_spike_multiplies_load():
    r = run_scenario(server_db(replicas=4), 1000, 0.9, scenario(multiplier=3))
    assert r.nodes["user"].rps == approx(3000) and r.nodes["server"].rps == approx(3000)
    assert r.nodes["db"].rps == approx(3000)

    # duration only stretches the queue backlog: (2 × 400 − 500) rps × 30 s
    r = run_scenario(server_queue(), 400, 0, scenario(multiplier=2, duration_s=30))
    assert r.nodes["queue"].backlog == approx(9000)


@pytest.mark.parametrize("mode", ["node", "replica"])  # replica of a one-copy Cache means node
def test_failure_cache_node_bypasses_to_db(mode):
    g = Graph(
        nodes=[
            node("user", "User"),
            node("server", "Server", replicas=2),
            node("cache", "Cache", hit_ratio=0.8),
            node("db", "Database"),
        ],
        edges=[
            Edge(source="user", target="server"),
            Edge(source="server", target="cache"),
            Edge(source="cache", target="db"),
        ],
    )
    r = run_scenario(g, 1000, 0.9, scenario(failure=Failure(type="Cache", mode=mode)))
    assert "cache" not in r.nodes
    assert r.nodes["db"].rps == approx(r.nodes["server"].rps) and r.nodes["db"].rps == approx(1000)
    assert r.error_rate == approx(0)


def test_bypass_multiplies_ratios_and_keeps_async():
    g = Graph(
        nodes=[
            node("user", "User"),
            node("server", "Server"),
            node("cache", "Cache"),
            node("db", "Database"),
        ],
        edges=[
            Edge(source="user", target="server"),
            Edge(source="server", target="cache", ratio=4),
            Edge(source="cache", target="db", kind="async", ratio=3),
        ],
    )
    failed, down = apply_failure(g, Failure(type="Cache", mode="node"), solve(g, 100, 0.9, 60))
    assert down == frozenset() and [n.id for n in failed.nodes] == ["user", "server", "db"]
    # 4 × 3 = 12 is above the editor's ratio limit of 10, and that is fine for the engine
    assert [(e.source, e.target, e.kind, e.ratio) for e in failed.edges] == [
        ("user", "server", "sync", 1),
        ("server", "db", "async", 12),
    ]
    assert len(g.nodes) == 4 and len(g.edges) == 3  # the student's graph is untouched


def test_failure_db_without_replicas_fails_all():
    sc = scenario(failure=Failure(type="Database", mode="replica"), max_error_rate=0.05)
    r = run_scenario(server_db(replicas=2), 1000, 0.9, sc)
    assert r.error_rate == approx(1) and not r.passed
    assert r.nodes["db"].capacity_rps == 0
    assert r.explanation == "База данных получает 1 000 rps при ёмкости 0: 100% запросов теряется"

    # the down node is the bottleneck even when a live node has a higher ρ (server 1.5 vs 1.0)
    r = run_scenario(server_db(replicas=1), 1000, 0.9, sc.model_copy(update={"multiplier": 1.5}))
    assert r.nodes["server"].rho == approx(1.5) and r.nodes["db"].rho == approx(1)
    assert r.bottleneck == "db"
    assert r.explanation == "База данных получает 1 000 rps при ёмкости 0: 100% запросов теряется"


def test_failure_db_with_replica_keeps_writes():
    g = server_db(replicas=4, read_replicas=1)
    r = run_scenario(g, 3000, 0.9, scenario(failure=Failure(type="Database", mode="replica")))
    # one replica gone, the primary alone serves 2000 of 3000
    assert r.nodes["db"].capacity_rps == 2000 and r.nodes["db"].errors_rps == approx(1000)
    assert r.error_rate == approx(1 / 3) and r.error_rate < 1
    assert g.nodes[2].params["read_replicas"] == 1  # the student's graph is untouched


def test_failure_type_absent_runs_unchanged():
    g = server_db(replicas=2)
    plain = run_scenario(g, 1000, 0.9, scenario(max_latency_ms=150))
    for mode in ("replica", "node"):
        sc = scenario(max_latency_ms=150, failure=Failure(type="Cache", mode=mode))
        assert run_scenario(g, 1000, 0.9, sc) == plain
    assert plain.passed

    # a Cache without edges takes no part in the run, so it cannot fail either
    g.nodes.append(node("cache", "Cache"))
    sc = scenario(max_latency_ms=150, failure=Failure(type="Cache", mode="node"))
    assert run_scenario(g, 1000, 0.9, sc) == plain


def test_failure_targets_most_loaded_node():
    def two_servers(share_a):
        # s_b comes first in the list, s_a first by id
        return Graph(
            nodes=[
                node("user", "User"),
                node("lb", "LoadBalancer"),
                node("s_b", "Server", replicas=2),
                node("s_a", "Server", replicas=2),
                node("db", "Database", read_replicas=2),
            ],
            edges=[
                Edge(source="user", target="lb"),
                Edge(source="lb", target="s_a", ratio=share_a),
                Edge(source="lb", target="s_b", ratio=1 - share_a),
                Edge(source="s_a", target="db"),
                Edge(source="s_b", target="db"),
            ],
        )

    def replicas_after_failure(g):
        failed, down = apply_failure(
            g, Failure(type="Server", mode="replica"), solve(g, 2000, 1, 60)
        )
        assert down == frozenset()
        return {n.id: n.params["replicas"] for n in failed.nodes if n.type == "Server"}

    assert replicas_after_failure(two_servers(0.3)) == {"s_b": 1, "s_a": 2}
    assert replicas_after_failure(two_servers(0.7)) == {"s_b": 2, "s_a": 1}
    assert replicas_after_failure(two_servers(0.5)) == {"s_b": 2, "s_a": 1}  # tie: first by id

    sc = scenario(failure=Failure(type="Server", mode="replica"), max_error_rate=0.01)
    r = run_scenario(two_servers(0.3), 2000, 1, sc)
    assert r.nodes["s_b"].capacity_rps == 1000 and r.bottleneck == "s_b" and not r.passed
    assert r.explanation == "Сервер s_b получает 1 400 rps при ёмкости 1 000: 29% запросов теряется"


def test_verdict_checks_all_targets():
    # server at ρ 1.2 in front of an overflowing queue: latency, errors and loss all non-zero
    g = server_queue(replicas=1, max_size=1000)
    r = run_scenario(g, 1200, 0, scenario())
    assert r.latency_ms == approx(600) and r.error_rate == approx(1 / 6)
    assert r.message_loss == approx(29 / 60)

    exact = dict(
        max_latency_ms=r.latency_ms, max_error_rate=r.error_rate, max_message_loss=r.message_loss
    )
    assert run_scenario(g, 1200, 0, scenario(**exact)).passed
    for key, value in exact.items():
        assert not run_scenario(g, 1200, 0, scenario(**{**exact, key: value * 0.99})).passed, key


def test_hidden_explanation_never_names_target():
    # targets chosen so that any rendering of them (123, 37%, 0.37, 29%, 0.29) is easy to spot
    targets = dict(max_latency_ms=123, max_error_rate=0.37, max_message_loss=0.29)
    cases = [
        # every template once: passed, overload, latency, queue loss
        (
            server_db(replicas=3),
            1,
            "Схема выдерживает сценарий; самое загруженное — База данных (50%)",
        ),
        (
            server_db(replicas=1),
            1.5,
            "Сервер получает 1 500 rps при ёмкости 1 000: 33% запросов теряется",
        ),
        (
            server_db(replicas=2, ratio=1.8),
            1,
            "Средняя задержка 420 мс; узкое место — База данных (загрузка 90%)",
        ),
        (
            server_queue(replicas=2),
            1,
            "Очередь теряет 48% сообщений: обработчики успевают 500 из 1 000 в секунду",
        ),
    ]
    for g, multiplier, text in cases:
        r = run_scenario(g, 1000, 0.9, scenario(visible=False, multiplier=multiplier, **targets))
        assert r.explanation == text
        assert not any(t in r.explanation for t in ("123", "37", "29")), r.explanation

    # the same latency failure, open to the student, names the target: the check above would see it
    r = run_scenario(server_db(replicas=2, ratio=1.8), 1000, 0.9, scenario(**targets))
    assert r.explanation == (
        "Средняя задержка 420 мс при цели 123 мс; узкое место — База данных (загрузка 90%)"
    )


def test_explanation_text_overloaded():
    r = run_scenario(
        server_db(replicas=4), 1000, 0.9, scenario(multiplier=3.2, max_error_rate=0.01)
    )
    assert not r.passed and r.bottleneck == "db"
    assert (
        r.explanation == "База данных получает 3 200 rps при ёмкости 2 000: 38% запросов теряется"
    )


def test_scenario_and_failure_reject_bad_input():
    with pytest.raises(ValidationError):
        scenario(target=1)  # unknown field
    with pytest.raises(ValidationError):
        scenario(multiplier=0)
    with pytest.raises(ValidationError):
        Failure(type="User", mode="node")  # removing User leaves nothing to run

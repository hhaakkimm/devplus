import pytest
from pydantic import ValidationError

from app.modules.simulator.engine.catalog import CATALOG, check_params
from app.modules.simulator.engine.graph import (
    Edge,
    Graph,
    Node,
    active_nodes,
    structural_errors,
    topo_order,
)


def node(id, type, **params):
    return Node(id=id, type=type, params=params)


def test_catalog_values_match_spec():
    assert CATALOG["Server"].capacity_rps == 1000 and CATALOG["Server"].latency_ms == 30
    assert CATALOG["Database"].capacity_rps == 2000 and CATALOG["Queue"].capacity_rps == 20000
    assert CATALOG["User"].capacity_rps is None
    assert {t for t, s in CATALOG.items() if s.terminal_ok} == {
        "Database",
        "Cache",
        "CDN",
        "Worker",
    }


def test_params_defaults_and_limits():
    assert check_params("Cache", {}) == {"hit_ratio": 0.8, "replicas": 1}
    assert check_params("Database", {}) == {"read_replicas": 0, "shards": 1}
    with pytest.raises(ValueError):
        check_params("Server", {"replicas": 0})
    with pytest.raises(ValueError):
        check_params("Server", {"replicas": 1.5})
    with pytest.raises(ValueError):
        check_params("Server", {"cores": 2})
    with pytest.raises(ValueError):
        check_params("Cache", {"hit_ratio": 1})


def test_node_params_are_checked_and_filled():
    assert node("c", "Cache").params == {"hit_ratio": 0.8, "replicas": 1}
    with pytest.raises(ValidationError):
        node("s", "Server", replicas=101)
    with pytest.raises(ValidationError):
        Node(id="bad id", type="Server")


def test_graph_rejects_dangling_edge_and_duplicate_ids():
    with pytest.raises(ValidationError):
        Graph(nodes=[node("u", "User")], edges=[Edge(source="u", target="ghost")])
    with pytest.raises(ValidationError):
        Graph(nodes=[node("u", "User"), node("u", "Server")], edges=[])


def test_edges_into_queue_and_worker_become_async():
    g = Graph(
        nodes=[node("u", "User"), node("q", "Queue"), node("w", "Worker"), node("s", "Server")],
        edges=[
            Edge(source="u", target="q"),
            Edge(source="q", target="w", kind="sync"),
            Edge(source="u", target="s"),
        ],
    )
    assert [e.kind for e in g.edges] == ["async", "async", "sync"]


def test_structural_errors_texts():
    ok = [node("u", "User"), node("s", "Server"), node("d", "Database")]
    # no User
    g = Graph(
        nodes=[node("s", "Server"), node("d", "Database")], edges=[Edge(source="s", target="d")]
    )
    assert structural_errors(g) == ["Нужен ровно один узел User"]
    # two Users
    g = Graph(
        nodes=[*ok, node("u2", "User")],
        edges=[Edge(source="u", target="s"), Edge(source="s", target="d")],
    )
    assert structural_errors(g) == ["Нужен ровно один узел User"]
    # cycle
    g = Graph(
        nodes=[*ok, node("s2", "Server")],
        edges=[
            Edge(source="u", target="s"),
            Edge(source="s", target="s2"),
            Edge(source="s2", target="s"),
            Edge(source="s2", target="d"),
        ],
    )
    assert structural_errors(g) == ["Схема содержит цикл"]
    # a node with edges that User cannot reach
    g = Graph(
        nodes=[*ok, node("s2", "Server")],
        edges=[
            Edge(source="u", target="s"),
            Edge(source="s", target="d"),
            Edge(source="s2", target="d"),
        ],
    )
    assert structural_errors(g) == ["Узел s2 недостижим от User"]
    # a Server leaf
    g = Graph(
        nodes=[*ok, node("s2", "Server")],
        edges=[
            Edge(source="u", target="s"),
            Edge(source="s", target="d"),
            Edge(source="s", target="s2"),
        ],
    )
    assert structural_errors(g) == [
        "Запросы из узла s2 уходят в никуда: добавь хранилище или обработчик"
    ]
    # a lone User has nowhere to send requests
    g = Graph(nodes=[node("u", "User")], edges=[])
    assert structural_errors(g) == [
        "Запросы из узла u уходят в никуда: добавь хранилище или обработчик"
    ]


def test_isolated_node_is_not_structural_error():
    g = Graph(
        nodes=[node("u", "User"), node("s", "Server"), node("d", "Database"), node("c", "Cache")],
        edges=[Edge(source="u", target="s"), Edge(source="s", target="d")],
    )
    assert structural_errors(g) == [] and "c" not in active_nodes(g)


def test_active_nodes_and_topo_order():
    g = Graph(
        nodes=[
            node("d", "Database"),
            node("s", "Server"),
            node("lb", "LoadBalancer"),
            node("u", "User"),
            node("c", "Cache"),
        ],
        edges=[
            Edge(source="s", target="d"),
            Edge(source="lb", target="s"),
            Edge(source="u", target="lb"),
        ],
    )
    assert active_nodes(g) == ["d", "s", "lb", "u"]
    assert topo_order(g) == ["u", "lb", "s", "d"]


def test_graph_size_limits():
    users = [node(f"n{i}", "Server") for i in range(51)]
    with pytest.raises(ValidationError):
        Graph(nodes=users, edges=[])
    two = [node("a", "Server"), node("b", "Server")]
    with pytest.raises(ValidationError):
        Graph(nodes=two, edges=[Edge(source="a", target="b")] * 101)
    Graph(nodes=users[:50], edges=[Edge(source="n0", target="n1")] * 100)

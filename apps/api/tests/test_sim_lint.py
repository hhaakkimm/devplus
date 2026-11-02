from app.modules.simulator.engine.graph import Edge, Graph, Node, structural_errors
from app.modules.simulator.engine.lint import Finding, lint


def build(nodes: str, *edges: str) -> Graph:
    """nodes: 'u:User s:Server', edges: 'u>s'; params as 's:Server:replicas=2'."""
    ns = []
    for spec in nodes.split():
        id_, type_, *rest = spec.split(":")
        params = (
            {k: float(v) for k, v in (p.split("=") for p in rest[0].split(","))} if rest else {}
        )
        ns.append(Node(id=id_, type=type_, params=params))
    es = [Edge(source=e.split(">")[0], target=e.split(">")[1]) for e in edges]
    return Graph(nodes=ns, edges=es)


def codes(g: Graph, read_ratio: float = 0.5) -> list[str]:
    return [f.code for f in lint(g, read_ratio)]


def nodes_of(g: Graph, code: str, read_ratio: float = 0.5) -> list[str | None]:
    return [f.node_id for f in lint(g, read_ratio) if f.code == code]


# STORAGE_EXPOSED
def test_storage_exposed_fires():
    g = build("u:User d:Database c:Cache", "u>d", "u>c")
    assert nodes_of(g, "STORAGE_EXPOSED") == ["c", "d"]
    f = next(f for f in lint(g, 0.5) if f.code == "STORAGE_EXPOSED")
    assert f.severity == "critical"
    assert f.message == "Хранилище доступно пользователю напрямую: между ними нужен сервер"


def test_storage_exposed_not_fires_behind_server():
    g = build("u:User s:Server d:Database", "u>s", "s>d")
    assert "STORAGE_EXPOSED" not in codes(g)


# QUEUE_NO_CONSUMER
def test_queue_no_consumer_fires():
    g = build("u:User s:Server q:Queue", "u>s", "s>q")
    assert nodes_of(g, "QUEUE_NO_CONSUMER") == ["q"]
    f = next(f for f in lint(g, 0.5) if f.code == "QUEUE_NO_CONSUMER")
    assert f.severity == "critical"
    assert f.message == "Сообщения из очереди никто не обрабатывает: добавь Worker"


def test_queue_no_consumer_not_fires_with_worker():
    g = build("u:User s:Server q:Queue w:Worker", "u>s", "s>q", "q>w")
    assert "QUEUE_NO_CONSUMER" not in codes(g)


# CACHE_BEHIND_DB
def test_cache_behind_db_fires_on_indirect_path():
    g = build("u:User s:Server d:Database x:Server c:Cache", "u>s", "s>d", "d>x", "x>c")
    assert nodes_of(g, "CACHE_BEHIND_DB") == ["c"]
    f = next(f for f in lint(g, 0.5) if f.code == "CACHE_BEHIND_DB")
    assert f.severity == "critical"
    assert f.message == "Кэш стоит после базы и не снимает с неё нагрузку"


def test_cache_behind_db_not_fires_cache_before_db():
    g = build("u:User s:Server c:Cache d:Database", "u>s", "s>c", "c>d")
    assert "CACHE_BEHIND_DB" not in codes(g)


def test_cache_behind_db_terminates_on_cycle():
    g = build("u:User d:Database x:Server c:Cache", "u>d", "d>x", "x>d", "x>c")
    assert nodes_of(g, "CACHE_BEHIND_DB") == ["c"]


# SINGLE_SERVER
def test_single_server_fires():
    g = build("u:User s:Server d:Database", "u>s", "s>d")
    assert nodes_of(g, "SINGLE_SERVER") == ["s"]
    f = next(f for f in lint(g, 0.5) if f.code == "SINGLE_SERVER")
    assert f.severity == "warning"
    assert f.message == "Один сервер без балансировщика — единая точка отказа"


def test_single_server_not_fires_behind_lb_but_fires_behind_cdn():
    behind_lb = build("u:User lb:LoadBalancer s:Server d:Database", "u>lb", "lb>s", "s>d")
    assert "SINGLE_SERVER" not in codes(behind_lb)
    behind_cdn = build("u:User cdn:CDN s:Server d:Database", "u>cdn", "cdn>s", "s>d")
    assert nodes_of(behind_cdn, "SINGLE_SERVER") == ["s"]


# REPLICAS_WITHOUT_LB
def test_replicas_without_lb_fires():
    g = build("u:User s:Server:replicas=3 d:Database", "u>s", "s>d")
    assert nodes_of(g, "REPLICAS_WITHOUT_LB") == ["s"]
    assert "SINGLE_SERVER" not in codes(g)
    f = next(f for f in lint(g, 0.5) if f.code == "REPLICAS_WITHOUT_LB")
    assert f.severity == "warning"
    assert f.message == "Копии сервера есть, а балансировщика перед ними нет"


def test_replicas_without_lb_not_fires_with_lb():
    g = build("u:User lb:LoadBalancer s:Server:replicas=3 d:Database", "u>lb", "lb>s", "s>d")
    assert "REPLICAS_WITHOUT_LB" not in codes(g)


# NO_CACHE_READ_HEAVY
def test_no_cache_read_heavy_fires():
    g = build("u:User s:Server d:Database", "u>s", "s>d")
    assert nodes_of(g, "NO_CACHE_READ_HEAVY", 0.8) == [None]
    f = next(f for f in lint(g, 0.8) if f.code == "NO_CACHE_READ_HEAVY")
    assert f.severity == "warning"
    assert f.message == "Чтений много, а кэша нет"


def test_no_cache_read_heavy_not_fires():
    plain = build("u:User s:Server d:Database", "u>s", "s>d")
    assert "NO_CACHE_READ_HEAVY" not in codes(plain, 0.79)
    with_cdn = build("u:User cdn:CDN s:Server d:Database", "u>cdn", "cdn>s", "s>d")
    assert "NO_CACHE_READ_HEAVY" not in codes(with_cdn, 0.9)


# DB_NO_REPLICAS
def test_db_no_replicas_fires():
    g = build("u:User s:Server d:Database", "u>s", "s>d")
    assert nodes_of(g, "DB_NO_REPLICAS") == ["d"]
    f = next(f for f in lint(g, 0.5) if f.code == "DB_NO_REPLICAS")
    assert f.severity == "warning"
    assert f.message == "У базы нет реплик: отказ primary остановит систему"


def test_db_no_replicas_not_fires_with_replicas():
    g = build("u:User s:Server d:Database:read_replicas=1", "u>s", "s>d")
    assert "DB_NO_REPLICAS" not in codes(g)


# WORKER_WITHOUT_QUEUE
def test_worker_without_queue_fires():
    g = build("u:User s:Server w:Worker", "u>s", "s>w")
    assert nodes_of(g, "WORKER_WITHOUT_QUEUE") == ["w"]
    f = next(f for f in lint(g, 0.5) if f.code == "WORKER_WITHOUT_QUEUE")
    assert f.severity == "warning"
    assert f.message == "Worker получает задачи не из очереди"


def test_worker_without_queue_not_fires_with_queue():
    g = build("u:User s:Server q:Queue w:Worker", "u>s", "s>q", "q>w")
    assert "WORKER_WITHOUT_QUEUE" not in codes(g)


# DEEP_SYNC_CHAIN: User is not counted
def test_deep_sync_chain_fires_on_six_nodes_after_user():
    g = build(
        "u:User a:CDN b:RateLimiter c:LoadBalancer d:Server e:Cache f:Database",
        "u>a", "a>b", "b>c", "c>d", "d>e", "e>f",
    )  # fmt: skip
    assert nodes_of(g, "DEEP_SYNC_CHAIN") == ["f"]
    f = next(f for f in lint(g, 0.5) if f.code == "DEEP_SYNC_CHAIN")
    assert f.severity == "warning"
    assert f.message == "Цепочка синхронных вызовов длиннее 5 узлов"


def test_deep_sync_chain_not_fires_on_five_nodes_after_user_or_async_tail():
    # the canonical chain: edge, balancer, server, cache, database
    five = build(
        "u:User a:CDN b:LoadBalancer c:Server d:Cache e:Database",
        "u>a", "a>b", "b>c", "c>d", "d>e",
    )  # fmt: skip
    assert "DEEP_SYNC_CHAIN" not in codes(five)
    # the edge into a Queue is async, so the sixth node is not on the sync path
    tail = build(
        "u:User a:CDN b:RateLimiter c:LoadBalancer d:Server e:Server q:Queue",
        "u>a", "a>b", "b>c", "c>d", "d>e", "e>q",
    )  # fmt: skip
    assert "DEEP_SYNC_CHAIN" not in codes(tail)


def test_deep_sync_chain_terminates_on_cycle():
    g = build("u:User a:Server b:Server", "u>a", "a>b", "b>a")
    assert "DEEP_SYNC_CHAIN" not in codes(g)


# ISOLATED_NODE
def test_isolated_node_fires():
    g = build("u:User s:Server d:Database c:Cache", "u>s", "s>d")
    assert nodes_of(g, "ISOLATED_NODE") == ["c"]
    f = next(f for f in lint(g, 0.5) if f.code == "ISOLATED_NODE")
    assert f.severity == "warning"
    assert f.message == "Узел ни с чем не связан и в расчёт не входит"


def test_isolated_node_not_fires_for_connected_nodes_and_lone_user():
    g = build("u:User s:Server d:Database", "u>s", "s>d")
    assert "ISOLATED_NODE" not in codes(g)
    # User always takes part in a run, so it is never reported as left out
    assert "ISOLATED_NODE" not in codes(build("u:User"))


def test_isolated_node_warning_only():
    g = build("u:User s:Server d:Database c:Cache", "u>s", "s>d")
    assert structural_errors(g) == []
    findings = lint(g, 0.9)
    assert (
        Finding("ISOLATED_NODE", "warning", "Узел ни с чем не связан и в расчёт не входит", "c")
        in findings
    )
    # the unconnected Cache does not count as a cache for NO_CACHE_READ_HEAVY
    assert "NO_CACHE_READ_HEAVY" in [f.code for f in findings]
    assert not any(f.node_id == "c" and f.code != "ISOLATED_NODE" for f in findings)


# ordering and safety
def test_findings_sorted_by_code_then_node_id():
    g = build("u:User s2:Server s1:Server", "u>s2", "u>s1")
    found = [(f.code, f.node_id) for f in lint(g, 0.5)]
    assert found == sorted(found, key=lambda p: (p[0], p[1] or ""))
    assert nodes_of(g, "SINGLE_SERVER") == ["s1", "s2"]


def test_lint_safe_without_user():
    g = build("s:Server d:Database", "s>d")
    assert "SINGLE_SERVER" in codes(g)

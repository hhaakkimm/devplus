"""Architecture rules: findings about a scheme that do not depend on a run."""

from dataclasses import dataclass
from typing import Literal

from app.modules.simulator.engine.graph import Graph, active_nodes


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Literal["critical", "warning"]
    message: str
    node_id: str | None


def _deep_sync_chain(start: str, children: dict[str, list[str]]) -> tuple[int, str]:
    """(nodes, last node) of the longest sync path from `start`, ignoring back edges."""
    best: dict[str, tuple[int, str]] = {}

    def walk(n: str, on_path: frozenset[str]) -> tuple[int, str]:
        if n in best:
            return best[n]
        res = (1, n)
        for c in sorted(children[n]):
            if c not in on_path:
                depth, last = walk(c, on_path | {n})
                if depth + 1 > res[0]:
                    res = (depth + 1, last)
        # ponytail: with a cycle the memo may undercount a path, the engine never runs such a graph
        best[n] = res
        return res

    return walk(start, frozenset())


def lint(g: Graph, read_ratio: float) -> list[Finding]:
    active = set(active_nodes(g))
    nodes = [n for n in g.nodes if n.id in active]
    types = {n.id: n.type for n in g.nodes}
    parents: dict[str, list[str]] = {n.id: [] for n in g.nodes}
    out: dict[str, list[str]] = {n.id: [] for n in g.nodes}
    sync: dict[str, list[str]] = {n.id: [] for n in g.nodes}
    for e in g.edges:
        parents[e.target].append(e.source)
        out[e.source].append(e.target)
        if e.kind == "sync":
            sync[e.source].append(e.target)

    found: list[Finding] = []

    def add(
        code: str, severity: Literal["critical", "warning"], message: str, node_id: str | None
    ) -> None:
        found.append(Finding(code, severity, message, node_id))

    # Database -> ... -> Cache: everything reachable from any database through at least one edge
    after_db: set[str] = set()
    stack = [t for n in nodes if n.type == "Database" for t in out[n.id]]
    while stack:
        i = stack.pop()
        if i not in after_db:
            after_db.add(i)
            stack += out[i]

    for n in nodes:
        parent_types = {types[p] for p in parents[n.id]}
        if n.type in ("Database", "Cache") and "User" in parent_types:
            add(
                "STORAGE_EXPOSED",
                "critical",
                "Хранилище доступно пользователю напрямую: между ними нужен сервер",
                n.id,
            )
        if n.type == "Queue" and not any(types[t] == "Worker" for t in out[n.id]):
            add(
                "QUEUE_NO_CONSUMER",
                "critical",
                "Сообщения из очереди никто не обрабатывает: добавь Worker",
                n.id,
            )
        if n.type == "Cache" and n.id in after_db:
            add(
                "CACHE_BEHIND_DB",
                "critical",
                "Кэш стоит после базы и не снимает с неё нагрузку",
                n.id,
            )
        if n.type == "Server" and "LoadBalancer" not in parent_types:
            if n.params["replicas"] == 1:
                add(
                    "SINGLE_SERVER",
                    "warning",
                    "Один сервер без балансировщика — единая точка отказа",
                    n.id,
                )
            else:
                add(
                    "REPLICAS_WITHOUT_LB",
                    "warning",
                    "Копии сервера есть, а балансировщика перед ними нет",
                    n.id,
                )
        if n.type == "Database" and n.params["read_replicas"] == 0:
            add(
                "DB_NO_REPLICAS",
                "warning",
                "У базы нет реплик: отказ primary остановит систему",
                n.id,
            )
        if n.type == "Worker" and "Queue" not in parent_types:
            add("WORKER_WITHOUT_QUEUE", "warning", "Worker получает задачи не из очереди", n.id)

    if read_ratio >= 0.8 and not any(n.type in ("Cache", "CDN") for n in nodes):
        add("NO_CACHE_READ_HEAVY", "warning", "Чтений много, а кэша нет", None)

    users = [n.id for n in g.nodes if n.type == "User"]
    if users:
        depth, last = _deep_sync_chain(users[0], sync)
        if depth - 1 > 5:  # User itself is not counted
            add("DEEP_SYNC_CHAIN", "warning", "Цепочка синхронных вызовов длиннее 5 узлов", last)

    # User always takes part in a run, so it is never "left out"
    for n in g.nodes:
        if n.id not in active:
            add("ISOLATED_NODE", "warning", "Узел ни с чем не связан и в расчёт не входит", n.id)

    return sorted(found, key=lambda f: (f.code, f.node_id or ""))

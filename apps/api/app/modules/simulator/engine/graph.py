"""The scheme a student draws: nodes, edges and the checks that decide whether it can be run."""

from collections import deque
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.simulator.engine.catalog import CATALOG, NodeType, check_params

NODE_ID = r"^[A-Za-z0-9_-]{1,40}$"


class Node(BaseModel):
    id: str = Field(pattern=NODE_ID)
    type: NodeType
    params: dict[str, float] = Field(default_factory=dict)
    # canvas position, the engine never reads it; jsonb cannot store NaN or Infinity
    x: float = Field(0, allow_inf_nan=False)
    y: float = Field(0, allow_inf_nan=False)

    @model_validator(mode="after")
    def fill_params(self) -> "Node":
        self.params = check_params(self.type, self.params)
        return self


class Edge(BaseModel):
    # the pattern keeps a lone surrogate out of the error message about a dangling edge
    source: str = Field(pattern=NODE_ID)
    target: str = Field(pattern=NODE_ID)
    kind: Literal["sync", "async"] = "sync"
    ratio: float = Field(1, ge=0, le=10)


class Graph(BaseModel):
    nodes: list[Node] = Field(max_length=50)
    edges: list[Edge] = Field(max_length=100)

    @model_validator(mode="after")
    def check_graph(self) -> "Graph":
        ids = [n.id for n in self.nodes]
        if len(set(ids)) != len(ids):
            raise ValueError("Узлы с одинаковым id")
        types = {n.id: n.type for n in self.nodes}
        for e in self.edges:
            if e.source not in types or e.target not in types:
                raise ValueError(f"Ребро {e.source} → {e.target} ведёт в несуществующий узел")
            if types[e.target] in ("Queue", "Worker"):
                e.kind = "async"
        return self


def active_nodes(g: Graph) -> list[str]:
    """Nodes with at least one edge, plus User; the rest take no part in a run."""
    touched = {e.source for e in g.edges} | {e.target for e in g.edges}
    return [n.id for n in g.nodes if n.id in touched or n.type == "User"]


def _topo(g: Graph) -> list[str] | None:
    """Kahn's algorithm over the active nodes, ties in the order of `g.nodes`; None on a cycle."""
    ids = active_nodes(g)
    indegree = dict.fromkeys(ids, 0)
    out: dict[str, list[str]] = {i: [] for i in ids}
    for e in g.edges:
        out[e.source].append(e.target)
        indegree[e.target] += 1
    queue = deque(i for i in ids if indegree[i] == 0)
    order: list[str] = []
    while queue:
        i = queue.popleft()
        order.append(i)
        for t in out[i]:
            indegree[t] -= 1
            if indegree[t] == 0:
                queue.append(t)
    return order if len(order) == len(ids) else None


def topo_order(g: Graph) -> list[str]:
    """Only for a graph without structural errors, so there is no cycle."""
    order = _topo(g)
    assert order is not None
    return order


def structural_errors(g: Graph) -> list[str]:
    users = [n.id for n in g.nodes if n.type == "User"]
    if len(users) != 1:
        return ["Нужен ровно один узел User"]
    errors: list[str] = []
    if _topo(g) is None:
        errors.append("Схема содержит цикл")
    out: dict[str, list[str]] = {n.id: [] for n in g.nodes}
    for e in g.edges:
        out[e.source].append(e.target)
    reached = {users[0]}
    stack = [users[0]]
    while stack:
        for t in out[stack.pop()]:
            if t not in reached:
                reached.add(t)
                stack.append(t)
    types = {n.id: n.type for n in g.nodes}
    active = active_nodes(g)
    errors += [f"Узел {i} недостижим от User" for i in active if i not in reached]
    errors += [
        f"Запросы из узла {i} уходят в никуда: добавь хранилище или обработчик"
        for i in active
        if i in reached and not out[i] and not CATALOG[types[i]].terminal_ok
    ]
    return errors

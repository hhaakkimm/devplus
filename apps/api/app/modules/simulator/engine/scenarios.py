"""Scenarios: load multiplier, one failure, verdict against the targets, Russian explanation."""

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.simulator.engine.catalog import CATALOG, NodeType
from app.modules.simulator.engine.graph import Edge, Graph
from app.modules.simulator.engine.solver import Flow, NodeMetrics, solve


class Failure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: NodeType
    mode: Literal["replica", "node"]

    @field_validator("type")
    @classmethod
    def not_user(cls, v: NodeType) -> NodeType:
        if v == "User":
            raise ValueError("Отказ узла User не моделируется")
        return v


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    visible: bool
    multiplier: float = Field(gt=0, le=100)
    duration_s: float = Field(60, gt=0, le=3600)
    failure: Failure | None = None
    max_latency_ms: float = Field(gt=0)
    max_error_rate: float = Field(ge=0, le=1)
    max_message_loss: float = Field(0, ge=0, le=1)


@dataclass(frozen=True)
class ScenarioResult:
    id: str
    title: str
    visible: bool
    passed: bool
    latency_ms: float
    error_rate: float
    rejected_rate: float
    message_loss: float
    bottleneck: str | None
    explanation: str
    nodes: dict[str, NodeMetrics]


def apply_failure(g: Graph, failure: Failure, normal: Flow) -> tuple[Graph, frozenset[str]]:
    """The failed copy of `g` and the nodes that are down; `g` itself is never changed."""
    hit = [m for m in normal.nodes.values() if m.type == failure.type]
    if not hit:
        return g, frozenset()
    target = min(hit, key=lambda m: (-m.rho, m.id)).id
    node = next(n for n in g.nodes if n.id == target)
    key, floor = ("read_replicas", 0) if node.type == "Database" else ("replicas", 1)
    if failure.mode == "replica" and node.params.get(key, floor) > floor:
        less = node.model_copy(update={"params": {**node.params, key: node.params[key] - 1}})
        nodes = [less if n is node else n for n in g.nodes]
        return g.model_copy(update={"nodes": nodes}), frozenset()
    outs = [e for e in g.edges if e.source == target]
    if not outs:
        return g, frozenset({target})
    # model_construct: a bypass may exceed the editor's ratio and edge limits, the engine copes
    bypass = [
        Edge.model_construct(
            source=a.source,
            target=b.target,
            kind="async" if "async" in (a.kind, b.kind) else "sync",
            ratio=a.ratio * b.ratio,
        )
        for a in g.edges
        if a.target == target
        for b in outs
    ]
    edges = [e for e in g.edges if target not in (e.source, e.target)] + bypass
    nodes = [n for n in g.nodes if n.id != target]
    return g.model_copy(update={"nodes": nodes, "edges": edges}), frozenset()


def _num(x: float) -> str:
    return f"{round(x):,}".replace(",", " ")


def run_scenario(g: Graph, peak_rps: float, read_ratio: float, sc: Scenario) -> ScenarioResult:
    """Only for a graph without structural errors, like `solve`."""
    failed, down = g, frozenset[str]()
    if sc.failure:
        normal = solve(g, peak_rps, read_ratio, sc.duration_s)
        failed, down = apply_failure(g, sc.failure, normal)
    flow = solve(failed, peak_rps * sc.multiplier, read_ratio, sc.duration_s, down)
    passed = (
        flow.latency_ms <= sc.max_latency_ms
        and flow.error_rate <= sc.max_error_rate
        and flow.message_loss <= sc.max_message_loss
    )

    # the most loaded node; a down node with traffic first, its ρ of 1 understates the outage
    b = min(
        (m for m in flow.nodes.values() if m.type != "User"),
        key=lambda m: (not (m.id in down and m.rps > 0), -m.rho, m.id),
    )
    many = Counter(n.type for n in g.nodes)

    def label(m: NodeMetrics) -> str:
        return CATALOG[m.type].label + (f" {m.id}" if many[m.type] > 1 else "")

    if passed:
        text = f"Схема выдерживает сценарий; самое загруженное — {label(b)} ({_num(b.rho * 100)}%)"
    elif flow.message_loss > sc.max_message_loss:
        q = max((m for m in flow.nodes.values() if m.type == "Queue"), key=lambda m: m.message_loss)
        workers = [
            flow.nodes[e.target]
            for e in failed.edges
            if e.source == q.id and flow.nodes[e.target].type == "Worker"
        ]
        mu = sum(w.capacity_rps or 0 for w in workers)
        text = (
            f"{label(q)} теряет {_num(q.message_loss * 100)}% сообщений: обработчики успевают "
            f"{_num(mu)} из {_num(sum(w.rps for w in workers))} в секунду"
        )
    elif b.rho >= 1:
        # errors_rps, not 1 − 1/ρ: a down node has ρ 1 and loses everything
        text = (
            f"{label(b)} получает {_num(b.rps)} rps при ёмкости {_num(b.capacity_rps or 0)}: "
            f"{_num(b.errors_rps / b.rps * 100)}% запросов теряется"
        )
    else:
        # shortcut: an error-rate failure with no node at ρ ≥ 1 (rate limiter rejections) gets
        # the latency text too, give it its own text if students find it confusing
        target = f" при цели {_num(sc.max_latency_ms)} мс" if sc.visible else ""
        text = (
            f"Средняя задержка {_num(flow.latency_ms)} мс{target}; "
            f"узкое место — {label(b)} (загрузка {_num(b.rho * 100)}%)"
        )

    return ScenarioResult(
        id=sc.id,
        title=sc.title,
        visible=sc.visible,
        passed=passed,
        latency_ms=flow.latency_ms,
        error_rate=flow.error_rate,
        rejected_rate=flow.rejected_rate,
        message_loss=flow.message_loss,
        bottleneck=b.id,
        explanation=text,
        nodes=flow.nodes,
    )

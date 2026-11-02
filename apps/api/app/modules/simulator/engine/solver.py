"""Flow solver: one pass over the scheme in topological order, spec section 3."""

import math
from dataclasses import astuple, dataclass, replace

from app.modules.simulator.engine.catalog import CATALOG, NodeType
from app.modules.simulator.engine.graph import Graph, topo_order


class EngineError(Exception):
    pass


@dataclass(frozen=True)
class NodeMetrics:
    id: str
    type: NodeType
    rps: float
    capacity_rps: float | None
    rho: float
    latency_ms: float
    errors_rps: float
    rejected_rps: float
    backlog: float
    message_loss: float


@dataclass(frozen=True)
class Flow:
    nodes: dict[str, NodeMetrics]
    latency_ms: float
    error_rate: float
    rejected_rate: float
    message_loss: float


def _share(mu: float, lam: float) -> float:
    """Served share min(1, μ/λ); 1 when nothing arrives."""
    return min(1.0, mu / lam) if lam > 0 else 1.0


def solve(
    g: Graph, rps: float, read_ratio: float, duration_s: float, down: frozenset[str] = frozenset()
) -> Flow:
    """Only for a graph without structural errors. `down` nodes serve nothing."""
    nodes = {n.id: n for n in g.nodes}
    order = topo_order(g)
    inflow = {i: (0.0, 0.0) for i in order}  # reads, writes
    from_queues: dict[str, dict[str, float]] = {i: {} for i in order}  # worker -> queue -> rps
    backlog = dict.fromkeys(order, 0.0)  # per queue, messages
    delivered = dict.fromkeys(order, 0.0)  # per queue, rps handed to workers
    f: dict[str, float] = {}  # served share, with the rate limiter's cut
    h: dict[str, float] = {}  # share a CDN or Cache answers itself
    metrics: dict[str, NodeMetrics] = {}

    for i in order:
        n, spec = nodes[i], CATALOG[nodes[i].type]
        reads, writes = (
            (rps * read_ratio, rps * (1 - read_ratio)) if n.type == "User" else inflow[i]
        )
        lam = reads + writes
        mu: float | None = None
        rho = errors = rejected = 0.0
        f[i], h[i], out = 1.0, 0.0, (reads, writes)
        if n.type == "User":
            pass
        elif i in down:
            # every request fails; ρ is 1 rather than λ/0 so the result stays finite
            mu, rho, errors, out = 0.0, float(lam > 0), lam, (0.0, 0.0)
            f[i] = _share(0, lam)
        elif n.type == "Database":
            cap = spec.capacity_rps or 0
            copies, shards = 1 + n.params["read_replicas"], n.params["shards"]
            lam_primary = (writes + reads / copies) / shards
            lam_replica = reads / copies / shards
            f_primary, f_replica = _share(cap, lam_primary), _share(cap, lam_replica)
            out = (reads / copies * (f_primary + (copies - 1) * f_replica), writes * f_primary)
            mu, rho = cap * copies * shards, max(lam_primary, lam_replica) / cap
            errors, f[i] = lam - sum(out), _share(sum(out), lam)
        else:
            copies = 1 if n.type in ("CDN", "RateLimiter", "Queue") else n.params["replicas"]
            mu, load, keep = (spec.capacity_rps or 0) * copies, lam, 1.0
            if n.type == "RateLimiter":
                load, keep = min(lam, n.params["limit_rps"]), _share(n.params["limit_rps"], lam)
                rejected = lam - load
            served = _share(mu, load)
            hit = n.params["hit_ratio"] if n.type in ("CDN", "Cache") else 0.0
            h[i] = reads * hit / lam if lam > 0 else 0.0
            out = (reads * keep * (1 - hit) * served, writes * keep * served)
            rho, f[i] = load / mu, keep * served
            queued = sum(from_queues[i].values())
            if n.type == "Worker" and queued > 0:
                # the excess waits in the queues, split by what each sends
                # shortcut: excess from direct (non-queue) edges into the same Worker is queued too,
                # split it out if mixed inputs ever matter
                for q, x in from_queues[i].items():
                    backlog[q] += max(0.0, load - mu) * duration_s * x / queued
                    delivered[q] += x
            else:
                errors = load * (1 - served)

        for e in g.edges:
            if e.source == i:
                r, w = inflow[e.target]
                inflow[e.target] = (r + out[0] * e.ratio, w + out[1] * e.ratio)
                if n.type == "Queue":
                    from_queues[e.target][i] = (
                        from_queues[e.target].get(i, 0.0) + sum(out) * e.ratio
                    )
        base = spec.latency_ms or 0.0
        metrics[i] = NodeMetrics(
            i, n.type, lam, mu, rho, base / (1 - min(rho, 0.95)), errors, rejected, 0.0, 0.0
        )

    loss = 0.0
    for i in order:
        if nodes[i].type == "Queue":
            max_size = nodes[i].params["max_size"]
            q_loss = (
                (backlog[i] - max_size) / (delivered[i] * duration_s)
                if backlog[i] > max_size
                else 0.0
            )
            metrics[i] = replace(metrics[i], backlog=backlog[i], message_loss=q_loss)
            loss = max(loss, q_loss)

    # end-to-end latency L and success share s over sync edges, children first
    L: dict[str, float] = {}
    s: dict[str, float] = {}
    for i in reversed(order):
        sync = [e for e in g.edges if e.source == i and e.kind == "sync"]
        L[i] = metrics[i].latency_ms + (1 - h[i]) * sum(e.ratio * L[e.target] for e in sync)
        ok = math.prod(1 - min(1.0, e.ratio * (1 - s[e.target])) for e in sync)
        s[i] = f[i] * (h[i] + (1 - h[i]) * ok)

    user = next(i for i in order if nodes[i].type == "User")
    flow = Flow(
        nodes=metrics,
        latency_ms=L[user],
        error_rate=1 - s[user],
        rejected_rate=sum(m.rejected_rps for m in metrics.values()) / rps if rps > 0 else 0.0,
        message_loss=loss,
    )
    values = [flow.latency_ms, flow.error_rate, flow.rejected_rate, flow.message_loss]
    values += [x for m in metrics.values() for x in astuple(m)[2:] if x is not None]
    if not all(math.isfinite(x) for x in values):
        raise EngineError("Расчёт дал нечисловой результат")
    return flow

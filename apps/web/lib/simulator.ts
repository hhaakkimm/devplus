// Pure helpers of the simulator workspace (client-safe): graph <-> API, the localStorage draft,
// node colouring. The limits mirror apps/api/app/modules/simulator; the API stays the authority.
import type { components } from "@devplus/api-client";
import type { Edge, Node } from "@xyflow/react";

type Schemas = components["schemas"];
export type ApiGraph = Schemas["SimGraph"];
export type Component = Schemas["SimComponentOut"];
export type Param = Schemas["SimParamOut"];
export type NodeType = Component["type"];
export type Answers = Schemas["SimAnswers"];
export type Draft = { graph: ApiGraph; answers: Answers };
export type RunOut = Schemas["SimRunOut"];
export type Metrics = Schemas["SimNodeMetricsOut"];
export type Finding = Schemas["SimFindingOut"];
export type Attempt = Schemas["SimAttemptOut"];

export type SimNodeData = { type: NodeType; params: Record<string, number> };
export type FlowNode = Node<SimNodeData, "sim">;
export type EdgeData = { kind: "sync" | "async"; ratio: number };
export type FlowEdge = Edge<EdgeData> & { data: EdgeData };

export const MAX_NODES = 50;
export const MAX_EDGES = 100;
export const MAX_ANSWER_CHARS = 5000;
const ID_RE = /^[A-Za-z0-9_-]{1,40}$/;

export const EMPTY_ANSWERS: Answers = {
  requirements: "",
  estimates: "",
  tradeoffs: "",
};

// The server turns every edge into Queue or Worker into async; the editor does it on connect.
export const ASYNC_ONLY: ReadonlySet<NodeType> = new Set(["Queue", "Worker"]);

// An edge's ratio, checked and edited like a node param.
export const RATIO: Param = {
  key: "ratio",
  label: "ratio",
  kind: "float",
  min: 0,
  max: 10,
  default: 1,
  help: "Сколько вызовов по связи приходится на один входящий запрос.",
};

export function paramError(p: Param, value: number): string | null {
  if (!Number.isFinite(value)) return "Введите число";
  if (value < p.min || value > p.max)
    return `Допустимо от ${p.min} до ${p.max}`;
  if (p.kind === "int" && !Number.isInteger(value)) return "Нужно целое число";
  return null;
}

export const defaultParams = (c: Component): Record<string, number> =>
  Object.fromEntries(c.params.map((p) => [p.key, p.default]));

export const flowNode = (
  id: string,
  data: SimNodeData,
  position: { x: number; y: number },
): FlowNode => ({
  id,
  type: "sim",
  position,
  data,
  ariaLabel: `Узел ${id}`,
});

// The API has no edge ids; the editor allows one edge per pair, and `>` never occurs in a node id.
export function flowEdge(
  source: string,
  target: string,
  data: EdgeData,
): FlowEdge {
  const label = [
    data.kind === "async" && "async",
    data.ratio !== 1 && `×${data.ratio}`,
  ]
    .filter(Boolean)
    .join(" ");
  return {
    id: `${source}->${target}`,
    source,
    target,
    data,
    animated: data.kind === "async",
    label: label || undefined,
    ariaLabel: `Связь ${source} → ${target}`,
  };
}

export function toApiGraph(nodes: FlowNode[], edges: FlowEdge[]): ApiGraph {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.data.type,
      params: n.data.params,
      x: n.position.x,
      y: n.position.y,
    })),
    edges: edges.map((e) => ({
      source: e.source,
      target: e.target,
      kind: e.data.kind,
      ratio: e.data.ratio,
    })),
  };
}

export function fromApiGraph(g: ApiGraph): {
  nodes: FlowNode[];
  edges: FlowEdge[];
} {
  return {
    nodes: g.nodes.map((n) =>
      flowNode(
        n.id,
        { type: n.type, params: n.params ?? {} },
        { x: n.x, y: n.y },
      ),
    ),
    edges: g.edges.map((e) =>
      flowEdge(e.source, e.target, { kind: e.kind, ratio: e.ratio }),
    ),
  };
}

// "server-1", "server-2", …: the first number not taken yet.
export function newNodeId(type: NodeType, existing: string[]): string {
  const taken = new Set(existing);
  const prefix = type.toLowerCase();
  for (let n = 1; ; n++) {
    if (!taken.has(`${prefix}-${n}`)) return `${prefix}-${n}`;
  }
}

export const heat = (rho: number): "ok" | "warm" | "hot" | "fail" =>
  rho < 0.7 ? "ok" : rho < 0.9 ? "warm" : rho < 1 ? "hot" : "fail";

// Numbers the Russian way: «20 000», «97,5%».
export const num = (n: number) => n.toLocaleString("ru-RU");
export const pct = (share: number) => `${num(+(share * 100).toFixed(2))}%`;
export const msText = (ms: number) => `${num(Math.round(ms))} мс`;

// «λ / μ rps» of a node in a scenario; User has no capacity.
export const loadText = (m: Metrics) =>
  m.capacity_rps == null
    ? `${num(Math.round(m.rps))} rps`
    : `${num(Math.round(m.rps))} / ${num(Math.round(m.capacity_rps))} rps`;

export const draftKey = (moduleSlug: string, slug: string) =>
  `devplus:sim:${moduleSlug}/${slug}`;

const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const isNum = (v: unknown): v is number =>
  typeof v === "number" && Number.isFinite(v);

// A stored draft checked against the current catalog; null when anything does not fit,
// e.g. a draft written before a type or a param left the catalog. Missing params get defaults.
function parseDraft(d: unknown, catalog: Component[]): Draft | null {
  if (!isObj(d) || !isObj(d.graph) || !isObj(d.answers)) return null;
  const { nodes, edges } = d.graph;
  if (!Array.isArray(nodes) || nodes.length > MAX_NODES) return null;
  if (!Array.isArray(edges) || edges.length > MAX_EDGES) return null;
  const specs = new Map<unknown, Component>(catalog.map((c) => [c.type, c]));
  const graph: ApiGraph = { nodes: [], edges: [] };
  const ids = new Set<string>();

  for (const n of nodes) {
    if (!isObj(n) || typeof n.id !== "string" || !ID_RE.test(n.id)) return null;
    const spec = specs.get(n.type);
    if (!spec || ids.has(n.id) || !isNum(n.x) || !isNum(n.y)) return null;
    if (!isObj(n.params)) return null;
    const stored = n.params;
    if (Object.keys(stored).some((k) => !spec.params.some((p) => p.key === k)))
      return null;
    const params: Record<string, number> = {};
    for (const p of spec.params) {
      const value = stored[p.key] ?? p.default;
      if (typeof value !== "number" || paramError(p, value)) return null;
      params[p.key] = value;
    }
    ids.add(n.id);
    graph.nodes.push({ id: n.id, type: spec.type, params, x: n.x, y: n.y });
  }

  const pairs = new Set<string>();
  for (const e of edges) {
    if (!isObj(e) || typeof e.source !== "string") return null;
    if (typeof e.target !== "string") return null;
    if (!ids.has(e.source) || !ids.has(e.target)) return null;
    if (e.kind !== "sync" && e.kind !== "async") return null;
    if (!isNum(e.ratio) || paramError(RATIO, e.ratio)) return null;
    const pair = `${e.source}->${e.target}`;
    if (pairs.has(pair)) return null;
    pairs.add(pair);
    graph.edges.push({
      source: e.source,
      target: e.target,
      kind: e.kind,
      ratio: e.ratio,
    });
  }

  const { requirements, estimates, tradeoffs } = d.answers;
  const answers = [requirements, estimates, tradeoffs];
  const fits = (a: unknown) =>
    typeof a === "string" && a.length <= MAX_ANSWER_CHARS;
  if (!answers.every(fits)) return null;
  return { graph, answers: { requirements, estimates, tradeoffs } as Answers };
}

// null: nothing stored (or storage is blocked); "reset": the stored draft is broken or stale.
export function loadDraft(
  key: string,
  catalog: Component[],
): Draft | "reset" | null {
  let raw: string | null;
  try {
    raw = localStorage.getItem(key);
  } catch {
    return null;
  }
  if (raw === null) return null;
  try {
    return parseDraft(JSON.parse(raw), catalog) ?? "reset";
  } catch {
    return "reset"; // broken JSON
  }
}

// false when the browser refuses to store it (blocked storage or no space left).
export function saveDraft(key: string, draft: Draft): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(draft));
    return true;
  } catch {
    return false;
  }
}

import { afterEach, beforeEach, expect, test, vi } from "vitest";
import {
  draftKey,
  fromApiGraph,
  graphKey,
  heat,
  loadDraft,
  loadText,
  msText,
  newNodeId,
  num,
  paramError,
  pct,
  saveDraft,
  toApiGraph,
  type ApiGraph,
  type Component,
  type Draft,
} from "@/lib/simulator";

const replicas = {
  key: "replicas",
  label: "Копий",
  kind: "int",
  min: 1,
  max: 100,
  default: 1,
  help: "",
} as const;
const hitRatio = {
  key: "hit_ratio",
  label: "Доля попаданий",
  kind: "float",
  min: 0,
  max: 0.99,
  default: 0.8,
  help: "",
} as const;
const component = (
  type: Component["type"],
  params: Component["params"] = [],
): Component => ({
  type,
  label: type,
  description: "",
  capacity_rps: null,
  latency_ms: null,
  params,
});
const CATALOG: Component[] = [
  component("User"),
  component("Server", [replicas]),
  component("Cache", [hitRatio, replicas]),
  component("Database"),
  component("Queue"),
];

const GRAPH: ApiGraph = {
  nodes: [
    { id: "user-1", type: "User", params: {}, x: 0, y: 0 },
    { id: "server-1", type: "Server", params: { replicas: 3 }, x: 240, y: -40 },
    {
      id: "cache-1",
      type: "Cache",
      params: { hit_ratio: 0.85, replicas: 2 },
      x: 480,
      y: 12.5,
    },
    { id: "db_main", type: "Database", params: {}, x: 720, y: 0 },
    { id: "queue-1", type: "Queue", params: {}, x: 480, y: 200 },
  ],
  edges: [
    { source: "user-1", target: "server-1", kind: "sync", ratio: 1 },
    { source: "server-1", target: "cache-1", kind: "sync", ratio: 2 },
    { source: "cache-1", target: "db_main", kind: "sync", ratio: 0.5 },
    { source: "server-1", target: "queue-1", kind: "async", ratio: 0 },
  ],
};
const ANSWERS = { requirements: "r", estimates: "e", tradeoffs: "t" };
const KEY = draftKey("system-design", "url-shortener");

// vitest runs in node: a Map stands in for the browser's storage.
beforeEach(() => {
  const store = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
  });
});
afterEach(() => vi.unstubAllGlobals());

// A stored draft with one change applied to its graph.
function storeWith(change: (g: ApiGraph) => void) {
  const graph: ApiGraph = structuredClone(GRAPH);
  change(graph);
  localStorage.setItem(KEY, JSON.stringify({ graph, answers: ANSWERS }));
}

test("toApiGraph/fromApiGraph round-trip keeps ids, params, kinds, ratios and positions", () => {
  const { nodes, edges } = fromApiGraph(GRAPH);
  expect(nodes[1]).toMatchObject({
    id: "server-1",
    position: { x: 240, y: -40 },
    data: { type: "Server", params: { replicas: 3 } },
  });
  expect(edges[3]).toMatchObject({
    source: "server-1",
    target: "queue-1",
    data: { kind: "async", ratio: 0 },
  });
  expect(new Set(edges.map((e) => e.id)).size).toBe(edges.length);
  expect(toApiGraph(nodes, edges)).toEqual(GRAPH);
});

test("loadDraft resets an unknown node type and a param out of range", () => {
  storeWith((g) => (g.nodes[3].type = "Kafka" as Component["type"]));
  expect(loadDraft(KEY, CATALOG)).toBe("reset");

  storeWith((g) => (g.nodes[1].params = { replicas: 0 }));
  expect(loadDraft(KEY, CATALOG)).toBe("reset");

  storeWith((g) => (g.nodes[1].params = { replicas: 1.5 }));
  expect(loadDraft(KEY, CATALOG)).toBe("reset");

  storeWith((g) => (g.nodes[2].params = { hit_ratio: 1 }));
  expect(loadDraft(KEY, CATALOG)).toBe("reset");

  storeWith((g) => (g.nodes[1].params = { replicas: 2, cores: 4 }));
  expect(loadDraft(KEY, CATALOG)).toBe("reset");

  storeWith((g) => (g.edges[0].ratio = 11));
  expect(loadDraft(KEY, CATALOG)).toBe("reset");

  storeWith((g) => (g.edges[0].target = "nowhere"));
  expect(loadDraft(KEY, CATALOG)).toBe("reset");

  storeWith((g) => (g.nodes[1].id = "user-1"));
  expect(loadDraft(KEY, CATALOG)).toBe("reset");
});

test("loadDraft returns a saved draft and fills a missing param with its default", () => {
  const draft: Draft = { graph: GRAPH, answers: ANSWERS };
  saveDraft(KEY, draft);
  expect(loadDraft(KEY, CATALOG)).toEqual(draft);

  storeWith((g) => (g.nodes[2].params = { replicas: 2 }));
  const loaded = loadDraft(KEY, CATALOG);
  expect(loaded).not.toBe("reset");
  expect((loaded as Draft).graph.nodes[2].params).toEqual({
    hit_ratio: 0.8,
    replicas: 2,
  });
});

test("loadDraft returns null when nothing is stored and 'reset' on broken JSON", () => {
  expect(KEY).toBe("devplus:sim:system-design/url-shortener");
  expect(loadDraft(KEY, CATALOG)).toBeNull();

  localStorage.setItem(KEY, "{oops");
  expect(loadDraft(KEY, CATALOG)).toBe("reset");

  localStorage.setItem(KEY, "null");
  expect(loadDraft(KEY, CATALOG)).toBe("reset");

  localStorage.setItem(KEY, JSON.stringify({ graph: GRAPH }));
  expect(loadDraft(KEY, CATALOG)).toBe("reset");
});

test("heat thresholds", () => {
  expect(heat(0.69)).toBe("ok");
  expect(heat(0.7)).toBe("warm");
  expect(heat(0.9)).toBe("hot");
  expect(heat(1)).toBe("fail");
});

test("newNodeId takes the first free number of the type", () => {
  expect(newNodeId("Server", [])).toBe("server-1");
  expect(newNodeId("Server", ["server-1", "server-2"])).toBe("server-3");
  expect(newNodeId("Server", ["server-2", "cache-1"])).toBe("server-1");
  expect(newNodeId("RateLimiter", [])).toMatch(/^[A-Za-z0-9_-]{1,40}$/);
});

test("paramError tells integers from fractions and checks the limits", () => {
  expect(paramError(replicas, 3)).toBeNull();
  expect(paramError(replicas, 1.5)).toBe("Нужно целое число");
  expect(paramError(replicas, 101)).toBe("Допустимо от 1 до 100");
  expect(paramError(hitRatio, 0.95)).toBeNull();
  expect(paramError(hitRatio, -0.1)).toBe("Допустимо от 0 до 0.99");
  expect(paramError(hitRatio, NaN)).toBe("Введите число");
});

// ru-RU groups digits with a no-break space and writes a decimal comma.
const ru = (s: string) => s.replace(/[\u00a0\u202f]/g, " ");

test("num, pct and msText format numbers the Russian way", () => {
  expect(ru(num(20000))).toBe("20 000");
  expect(ru(pct(0.975))).toBe("97,5%");
  expect(pct(0.05)).toBe("5%");
  expect(pct(0.012345)).toBe("1,23%");
  expect(pct(0)).toBe("0%");
  expect(ru(msText(1234.6))).toBe("1 235 мс");
  expect(msText(2.04)).toBe("2 мс");
});

test("loadText is «λ / μ rps», only λ for a node without a capacity", () => {
  const m = {
    id: "server-1",
    type: "Server" as const,
    rps: 19999.6,
    capacity_rps: 1000,
    rho: 20,
    latency_ms: 600,
    errors_rps: 19000,
    rejected_rps: 0,
    backlog: 0,
    message_loss: 0,
  };
  expect(ru(loadText(m))).toBe("20 000 / 1 000 rps");
  expect(ru(loadText({ ...m, type: "User", capacity_rps: null }))).toBe(
    "20 000 rps",
  );
});

test("graphKey ignores coordinates and order, and changes with anything the engine reads", () => {
  const key = graphKey(GRAPH);
  const changed = (change: (g: ApiGraph) => void) => {
    const g: ApiGraph = structuredClone(GRAPH);
    change(g);
    return graphKey(g);
  };
  // moving a node or listing nodes and edges in another order is the same scheme
  expect(changed((g) => (g.nodes[1].x += 100))).toBe(key);
  expect(changed((g) => (g.nodes[1].y = -1))).toBe(key);
  expect(changed((g) => g.nodes.reverse())).toBe(key);
  expect(changed((g) => g.edges.reverse())).toBe(key);
  expect(
    changed((g) => (g.nodes[2].params = { replicas: 2, hit_ratio: 0.85 })),
  ).toBe(key);
  // a param, an edge kind or ratio, an id, a type or an edge more or less is another scheme
  expect(changed((g) => (g.nodes[1].params = { replicas: 20 }))).not.toBe(key);
  expect(changed((g) => (g.edges[0].kind = "async"))).not.toBe(key);
  expect(changed((g) => (g.edges[1].ratio = 1))).not.toBe(key);
  expect(changed((g) => (g.nodes[3].id = "db-2"))).not.toBe(key);
  expect(changed((g) => (g.nodes[4].type = "Worker"))).not.toBe(key);
  expect(changed((g) => g.edges.pop())).not.toBe(key);
});

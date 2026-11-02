"use client";

import {
  applyEdgeChanges,
  applyNodeChanges,
  ReactFlowProvider,
  useReactFlow,
  useStoreApi,
  type Connection,
  type EdgeChange,
  type NodeChange,
  type XYPosition,
} from "@xyflow/react";
import {
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { ErrorList } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Answers } from "@/components/simulator/answers";
import { Attempts } from "@/components/simulator/attempts";
import { Canvas } from "@/components/simulator/canvas";
import { Inspector } from "@/components/simulator/inspector";
import { Palette } from "@/components/simulator/palette";
import { Results, type Result } from "@/components/simulator/results";
import { ScenarioSwitch } from "@/components/simulator/scenario-switch";
import {
  CatalogContext,
  MetricsContext,
} from "@/components/simulator/sim-node";
import { useHistory } from "@/components/simulator/use-history";
import { Button } from "@/components/ui/button";
import { browserApi } from "@/lib/browser-api";
import { dateText } from "@/lib/runs";
import {
  ASYNC_ONLY,
  defaultParams,
  draftKey,
  EMPTY_ANSWERS,
  flowEdge,
  flowNode,
  fromApiGraph,
  loadDraft,
  MAX_EDGES,
  MAX_NODES,
  newNodeId,
  saveDraft,
  toApiGraph,
  type Attempt,
  type Component,
  type EdgeData,
  type FlowEdge,
  type FlowNode,
  type Metrics,
  type NodeType,
} from "@/lib/simulator";

type Props = {
  module: string;
  slug: string;
  catalog: Component[];
  attempts: Attempt[]; // the user's attempts at the task, newest first
  statement: ReactNode; // the «Условие» tab, rendered on the server
};
type Tab = "statement" | "answers" | "results" | "attempts";
// an attempt shown read-only instead of the draft
type View = { attempt: Attempt; nodes: FlowNode[]; edges: FlowEdge[] };

const TABS: [Tab, string][] = [
  ["statement", "Условие"],
  ["answers", "Ответы"],
  ["results", "Результаты"],
  ["attempts", "Попытки"],
];
const DEBOUNCE_MS = 500;
const NODE_SIZE = { width: 160, height: 64 }; // about the size of SimNode, to centre a new node
const GRID =
  "lg:grid lg:h-[75vh] lg:min-h-[32rem] lg:grid-cols-[13rem_minmax(0,1fr)_24rem] lg:gap-4";

const noSubscribe = () => () => {};

// The draft lives in localStorage, which the server cannot read: the editor renders only in the
// browser, the server sends the statement in the same place.
export function Workspace(props: Props) {
  const browser = useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
  if (!browser)
    return (
      <div className={GRID}>
        <div className="hidden lg:block" />
        <div className="hidden rounded-lg border lg:block" />
        <div className="overflow-y-auto">{props.statement}</div>
      </div>
    );
  return (
    <ReactFlowProvider>
      <Editor {...props} />
    </ReactFlowProvider>
  );
}

function Editor({ module, slug, catalog, attempts, statement }: Props) {
  const key = draftKey(module, slug);
  const [specs] = useState(() => new Map(catalog.map((c) => [c.type, c])));
  const [start] = useState(() => {
    const draft = loadDraft(key, catalog);
    const ok = draft !== null && draft !== "reset";
    return {
      ...(ok ? fromApiGraph(draft.graph) : { nodes: [], edges: [] }),
      answers: ok ? draft.answers : EMPTY_ANSWERS,
      notice: draft === "reset" ? "Черновик устарел и сброшен" : null,
    };
  });
  const [nodes, setNodes] = useState<FlowNode[]>(start.nodes);
  const [edges, setEdges] = useState<FlowEdge[]>(start.edges);
  const [answers, setAnswers] = useState(start.answers);
  const [notice, setNotice] = useState<string | null>(start.notice);
  const [saved, setSaved] = useState(true);
  const [tab, setTab] = useState<Tab>("statement");
  // shortcut: results and node colours stay after an edit until the next run, mark them stale
  // if students take old numbers for new ones
  const [result, setResult] = useState<Result | null>(null);
  const [scenario, setScenario] = useState(""); // the run's scenario on the canvas
  const [view, setView] = useState<View | null>(null);
  const store = useStoreApi<FlowNode, FlowEdge>();
  const { fitView } = useReactFlow<FlowNode, FlowEdge>();
  const record = useHistory(nodes, edges, setNodes, setEdges, !view);
  const running = useAction();
  const sending = useAction();
  const busy = running.busy || sending.busy;
  const run = !view && result && "run" in result ? result.run : null;
  const metrics = useMemo(
    () =>
      new Map<string, Metrics>(
        run?.scenarios
          .find((s) => s.id === scenario)
          ?.nodes.map((m) => [m.id, m]),
      ),
    [run, scenario],
  );

  // shortcut: a tab closed or an in-app navigation within 500 ms of an edit loses that edit,
  // flush on pagehide and unmount if students lose work
  // shortcut: two browser tabs on the same task overwrite each other's draft (last write wins),
  // add a storage-event merge if it ever matters
  useEffect(() => {
    const timer = setTimeout(
      () =>
        setSaved(saveDraft(key, { graph: toApiGraph(nodes, edges), answers })),
      DEBOUNCE_MS,
    );
    return () => clearTimeout(timer);
  }, [key, nodes, edges, answers]);

  // Before every edit; selection and the moves of a drag are not edits, the drag start is.
  function remember() {
    record();
    setNotice(null);
  }

  const hasUser = nodes.some((n) => n.data.type === "User");
  const full = nodes.length >= MAX_NODES;

  // `at` is where the middle of the node goes; without it, the middle of the visible canvas
  function add(type: NodeType, at?: XYPosition) {
    const spec = specs.get(type);
    if (!spec || full || (type === "User" && hasUser)) return;
    const { width, height, transform } = store.getState();
    const [panX, panY, zoom] = transform;
    const centre = at ?? {
      x: (width / 2 - panX) / zoom,
      y: (height / 2 - panY) / zoom,
    };
    const position = {
      x: Math.round(centre.x - NODE_SIZE.width / 2),
      y: Math.round(centre.y - NODE_SIZE.height / 2),
    };
    // repeated clicks put nodes in a row instead of on top of each other, where they hide the ports
    const covered = () =>
      nodes.some(
        (n) =>
          Math.abs(n.position.x - position.x) < NODE_SIZE.width &&
          Math.abs(n.position.y - position.y) < NODE_SIZE.height,
      );
    while (!at && covered()) position.x += NODE_SIZE.width + 40;
    remember();
    const id = newNodeId(
      type,
      nodes.map((n) => n.id),
    );
    const node = flowNode(id, { type, params: defaultParams(spec) }, position);
    setNodes([
      ...nodes.map((n) => ({ ...n, selected: false })),
      { ...node, selected: true }, // the inspector opens on it
    ]);
  }

  function connect(c: Connection) {
    const target = nodes.find((n) => n.id === c.target);
    if (!target) return;
    if (edges.length >= MAX_EDGES) {
      setNotice(`На схеме не больше ${MAX_EDGES} связей`);
      return;
    }
    remember();
    const kind = ASYNC_ONLY.has(target.data.type) ? "async" : "sync";
    setEdges([...edges, flowEdge(c.source, c.target, { kind, ratio: 1 })]);
  }

  function setParam(id: string, key: string, value: number) {
    const node = nodes.find((n) => n.id === id);
    if (!node || node.data.params[key] === value) return;
    remember();
    const params = { ...node.data.params, [key]: value };
    setNodes(
      nodes.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, params } } : n,
      ),
    );
  }

  function setEdgeData(id: string, data: EdgeData) {
    const edge = edges.find((e) => e.id === id);
    if (
      !edge ||
      (edge.data.kind === data.kind && edge.data.ratio === data.ratio)
    )
      return;
    remember();
    setEdges(
      edges.map((e) =>
        e.id === id ? { ...e, ...flowEdge(e.source, e.target, data) } : e,
      ),
    );
  }

  const path = { params: { path: { module, task: slug } } };

  function runScheme() {
    sending.setError(null);
    running.run(
      () =>
        browserApi.POST("/api/simulator/tasks/{module}/{task}/run", {
          ...path,
          body: { graph: toApiGraph(nodes, edges) },
        }),
      (data) => {
        setResult({ run: data });
        // the same scenario stays on the canvas from run to run
        const ids = data.scenarios.map((s) => s.id);
        setScenario((id) => (ids.includes(id) ? id : (ids[0] ?? "")));
        setTab("results");
      },
    );
  }

  function send() {
    running.setError(null);
    sending.run(
      () =>
        browserApi.POST("/api/simulator/tasks/{module}/{task}/attempts", {
          ...path,
          body: { graph: toApiGraph(nodes, edges), answers },
        }),
      (data) => {
        setResult({ attempt: data });
        setTab("results");
        sending.router.refresh(); // the new attempt in «Попытки»
      },
    );
  }

  // A finding's node: selected (on the draft) and in the middle of the canvas.
  function focus(id: string) {
    if (!(view?.nodes ?? nodes).some((n) => n.id === id)) return;
    if (!view) setNodes(nodes.map((n) => ({ ...n, selected: n.id === id })));
    void fitView({ nodes: [{ id }], maxZoom: 1, duration: 300 });
  }

  function startOver() {
    if (!window.confirm("Удалить схему и ответы?")) return;
    remember();
    setNodes([]);
    setEdges([]);
    setAnswers(EMPTY_ANSWERS);
  }

  const selected = nodes.filter((n) => n.selected);
  const node = selected.length === 1 ? selected[0] : undefined;
  const errors = [running.error, sending.error].filter((e) => e !== null);
  const panels: Record<Tab, ReactNode> = {
    statement,
    answers: (
      <Answers
        answers={view ? view.attempt.answers : answers}
        onChange={view ? undefined : setAnswers}
      />
    ),
    results: (
      <Results
        result={view ? { attempt: view.attempt } : result}
        onFocus={focus}
      />
    ),
    attempts: (
      <Attempts
        attempts={attempts}
        shown={view?.attempt.id}
        onOpen={(a) => setView({ attempt: a, ...fromApiGraph(a.graph) })}
      />
    ),
  };

  return (
    <CatalogContext value={specs}>
      <p className="mb-4 rounded-lg border p-4 text-sm text-muted-foreground lg:hidden">
        Редактор доступен на компьютере
      </p>
      <div className={GRID}>
        <aside
          aria-label="Компоненты и параметры"
          className="hidden content-start gap-6 overflow-y-auto pr-1 lg:grid"
        >
          {!view && (
            <>
              <Palette
                catalog={catalog}
                full={full}
                hasUser={hasUser}
                onAdd={(type) => add(type)}
              />
              <Inspector
                node={node}
                spec={node && specs.get(node.data.type)}
                onParam={(k, v) => node && setParam(node.id, k, v)}
              />
            </>
          )}
        </aside>
        <div className="hidden min-h-0 flex-col gap-2 lg:flex">
          <div className="flex flex-wrap items-center gap-3">
            {view ? (
              <>
                <p className="text-sm">
                  Попытка {dateText(view.attempt.created_at)}, только просмотр
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setView(null)}
                >
                  Вернуться к черновику
                </Button>
              </>
            ) : (
              <>
                <Button
                  type="button"
                  size="sm"
                  disabled={busy}
                  onClick={runScheme}
                >
                  Прогнать
                </Button>
                <Button type="button" size="sm" disabled={busy} onClick={send}>
                  Отправить
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={busy}
                  onClick={startOver}
                >
                  Начать заново
                </Button>
              </>
            )}
            {sending.busy && (
              <p role="status" className="text-sm">
                Разбираем решение…
              </p>
            )}
            {run && run.scenarios.length > 0 && (
              <ScenarioSwitch
                scenarios={run.scenarios}
                value={scenario}
                onChange={setScenario}
              />
            )}
            {notice && (
              <p role="status" className="text-sm text-muted-foreground">
                {notice}
              </p>
            )}
            {!saved && (
              <p role="alert" className="text-sm text-destructive">
                Черновик не сохраняется: браузер не даёт записать его
              </p>
            )}
          </div>
          <ErrorList messages={errors} />
          <div className="min-h-0 flex-1">
            <MetricsContext value={metrics}>
              {view ? (
                // a key per scheme: React Flow starts over and fits it in view
                <Canvas
                  key={view.attempt.id}
                  nodes={view.nodes}
                  edges={view.edges}
                />
              ) : (
                <Canvas
                  key="draft"
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={(changes: NodeChange<FlowNode>[]) =>
                    setNodes((ns) => applyNodeChanges(changes, ns))
                  }
                  onEdgesChange={(changes: EdgeChange<FlowEdge>[]) =>
                    setEdges((es) => applyEdgeChanges(changes, es))
                  }
                  onConnect={connect}
                  isValidConnection={(c) =>
                    c.source !== c.target &&
                    !edges.some(
                      (e) => e.source === c.source && e.target === c.target,
                    )
                  }
                  // React Flow calls it on every Delete/Backspace, also with nothing selected
                  onBeforeDelete={async (d) => {
                    if (d.nodes.length > 0 || d.edges.length > 0) remember();
                    return true;
                  }}
                  onNodeDragStart={() => remember()}
                  onDropType={add}
                  onEdgeData={setEdgeData}
                />
              )}
            </MetricsContext>
          </div>
        </div>
        <section aria-label="Задача" className="min-h-0 overflow-y-auto">
          <div role="tablist" className="mb-4 hidden gap-1 border-b lg:flex">
            {TABS.map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                id={`sim-tab-${id}`}
                aria-selected={tab === id}
                aria-controls={`sim-panel-${id}`}
                onClick={() => setTab(id)}
                className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === id ? "border-primary font-medium" : "border-transparent text-muted-foreground hover:text-foreground"}`}
              >
                {label}
              </button>
            ))}
          </div>
          {TABS.map(([id]) => (
            <div
              key={id}
              role="tabpanel"
              id={`sim-panel-${id}`}
              aria-labelledby={`sim-tab-${id}`}
              // below 1024 px only the statement is shown, whatever tab was picked
              className={
                id === "statement"
                  ? tab === id
                    ? ""
                    : "lg:hidden"
                  : tab === id
                    ? "hidden lg:block"
                    : "hidden"
              }
            >
              {panels[id]}
            </div>
          ))}
        </section>
      </div>
    </CatalogContext>
  );
}

"use client";

import {
  applyEdgeChanges,
  applyNodeChanges,
  ReactFlowProvider,
  useStoreApi,
  type Connection,
  type EdgeChange,
  type NodeChange,
  type XYPosition,
} from "@xyflow/react";
import {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
  type RefObject,
} from "react";
import { Canvas } from "@/components/simulator/canvas";
import { Inspector } from "@/components/simulator/inspector";
import { Palette } from "@/components/simulator/palette";
import { CatalogContext } from "@/components/simulator/sim-node";
import { Button } from "@/components/ui/button";
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
  type Component,
  type EdgeData,
  type FlowEdge,
  type FlowNode,
  type NodeType,
} from "@/lib/simulator";

type Props = {
  module: string;
  slug: string;
  catalog: Component[];
  statement: ReactNode; // the «Условие» tab, rendered on the server
};
type Tab = "statement" | "answers" | "results" | "attempts";
type Snapshot = { nodes: FlowNode[]; edges: FlowEdge[] };

const TABS: [Tab, string][] = [
  ["statement", "Условие"],
  ["answers", "Ответы"],
  ["results", "Результаты"],
  ["attempts", "Попытки"],
];
const DEBOUNCE_MS = 500;
// shortcut: undo keeps the last 50 edits in memory only, persist it if students ask for more
const HISTORY_DEPTH = 50;
const NODE_SIZE = { width: 160, height: 64 }; // about the size of SimNode, to centre a new node
const GRID =
  "lg:grid lg:h-[75vh] lg:min-h-[32rem] lg:grid-cols-[13rem_minmax(0,1fr)_24rem] lg:gap-4";

const noSubscribe = () => () => {};
const isEditable = (t: EventTarget | null) =>
  t instanceof HTMLElement &&
  (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName));

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

function Editor({ module, slug, catalog, statement }: Props) {
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
  const store = useStoreApi<FlowNode, FlowEdge>();
  const past = useRef<Snapshot[]>([]);
  const future = useRef<Snapshot[]>([]);

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
    past.current = [...past.current, { nodes, edges }].slice(-HISTORY_DEPTH);
    future.current = [];
    setNotice(null);
  }

  function travel(from: RefObject<Snapshot[]>, to: RefObject<Snapshot[]>) {
    const snapshot = from.current.pop();
    if (!snapshot) return;
    to.current.push({ nodes, edges });
    setNodes(snapshot.nodes);
    setEdges(snapshot.edges);
  }

  // on the document: after Delete the removed node had the focus; typing keeps its own undo
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey) || isEditable(e.target)) return;
      // e.code, not e.key: the same keys in the Russian layout
      if (e.code === "KeyZ" && !e.shiftKey) travel(past, future);
      else if (e.code === "KeyY" || (e.code === "KeyZ" && e.shiftKey))
        travel(future, past);
      else return;
      e.preventDefault();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  });

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

  function startOver() {
    if (!window.confirm("Удалить схему и ответы?")) return;
    remember();
    setNodes([]);
    setEdges([]);
    setAnswers(EMPTY_ANSWERS);
  }

  const selected = nodes.filter((n) => n.selected);
  const node = selected.length === 1 ? selected[0] : undefined;

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
        </aside>
        <div className="hidden min-h-0 flex-col gap-2 lg:flex">
          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={startOver}
            >
              Начать заново
            </Button>
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
          <div className="min-h-0 flex-1">
            <Canvas
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
              {id === "statement" ? (
                statement
              ) : (
                <p className="text-sm text-muted-foreground">Пока пусто.</p>
              )}
            </div>
          ))}
        </section>
      </div>
    </CatalogContext>
  );
}

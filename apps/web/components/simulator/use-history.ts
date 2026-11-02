import { useEffect, useRef, type RefObject } from "react";
import type { FlowEdge, FlowNode } from "@/lib/simulator";

type Snapshot = { nodes: FlowNode[]; edges: FlowEdge[] };

// shortcut: undo keeps the last 50 edits in memory only, persist it if students ask for more
const HISTORY_DEPTH = 50;

const isEditable = (t: EventTarget | null) =>
  t instanceof HTMLElement &&
  (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName));

// Undo and redo of the scheme: `remember` goes before every edit; selection and the moves of a
// drag are not edits, the drag start is. Ctrl+Z / Ctrl+Y (and Ctrl+Shift+Z) act while `enabled`.
export function useHistory(
  nodes: FlowNode[],
  edges: FlowEdge[],
  setNodes: (nodes: FlowNode[]) => void,
  setEdges: (edges: FlowEdge[]) => void,
  enabled: boolean,
) {
  const past = useRef<Snapshot[]>([]);
  const future = useRef<Snapshot[]>([]);

  function remember() {
    past.current = [...past.current, { nodes, edges }].slice(-HISTORY_DEPTH);
    future.current = [];
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
      if (!enabled || !(e.ctrlKey || e.metaKey) || isEditable(e.target)) return;
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

  return remember;
}

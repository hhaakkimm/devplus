import { Handle, Position, type NodeProps } from "@xyflow/react";
import { createContext, useContext } from "react";
import {
  heat,
  loadText,
  type Component,
  type FlowNode,
  type Metrics,
  type NodeType,
} from "@/lib/simulator";

// Labels come from the API catalog; React Flow renders nodes by type, so it reaches them via context.
export const CatalogContext = createContext<Map<NodeType, Component>>(
  new Map(),
);
// The nodes' load in the scenario picked after a run, by node id; empty when nothing is shown.
export const MetricsContext = createContext<Map<string, Metrics>>(new Map());

// Ports bigger than React Flow's 6 px default: easier to hit with a mouse.
const PORT = { width: 10, height: 10 };
const HEAT = {
  ok: "border-green-600 bg-green-500/10",
  warm: "border-yellow-500 bg-yellow-400/15",
  hot: "border-orange-500 bg-orange-500/15",
  fail: "border-red-600 bg-red-500/15",
};

export function SimNode({ id, data, selected }: NodeProps<FlowNode>) {
  const spec = useContext(CatalogContext).get(data.type);
  const m = useContext(MetricsContext).get(id);
  // User has no capacity, so nothing to colour
  const tone =
    m && m.capacity_rps != null
      ? `border-2 ${HEAT[heat(m.rho)]}`
      : `border bg-background ${selected ? "border-primary" : ""}`;
  return (
    <div
      className={`w-40 rounded-md px-3 py-2 text-xs shadow-sm ${tone} ${selected ? "ring-2 ring-primary/40" : ""}`}
    >
      {/* User only sends requests */}
      {data.type !== "User" && (
        <Handle type="target" position={Position.Left} style={PORT} />
      )}
      <p className="text-sm font-medium">{spec?.label ?? data.type}</p>
      <p className="text-muted-foreground">{id}</p>
      {spec?.params.map((p) => (
        <p key={p.key}>
          {p.label}: {data.params[p.key]}
        </p>
      ))}
      {m && <p className="mt-1 font-medium">{loadText(m)}</p>}
      <Handle type="source" position={Position.Right} style={PORT} />
    </div>
  );
}

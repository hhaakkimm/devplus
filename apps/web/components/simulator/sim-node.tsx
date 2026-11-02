import { Handle, Position, type NodeProps } from "@xyflow/react";
import { createContext, useContext } from "react";
import type { Component, FlowNode, NodeType } from "@/lib/simulator";

// Labels come from the API catalog; React Flow renders nodes by type, so it reaches them via context.
export const CatalogContext = createContext<Map<NodeType, Component>>(
  new Map(),
);

// Ports bigger than React Flow's 6 px default: easier to hit with a mouse.
const PORT = { width: 10, height: 10 };

export function SimNode({ id, data, selected }: NodeProps<FlowNode>) {
  const spec = useContext(CatalogContext).get(data.type);
  return (
    <div
      className={`w-40 rounded-md border bg-background px-3 py-2 text-xs shadow-sm ${selected ? "border-primary ring-2 ring-primary/40" : ""}`}
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
      <Handle type="source" position={Position.Right} style={PORT} />
    </div>
  );
}

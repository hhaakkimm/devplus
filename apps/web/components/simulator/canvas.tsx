import {
  Background,
  Controls,
  ReactFlow,
  useReactFlow,
  type ReactFlowProps,
  type XYPosition,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useRef, useState } from "react";
import { EdgePopover } from "@/components/simulator/edge-popover";
import { DRAG_TYPE } from "@/components/simulator/palette";
import { SimNode } from "@/components/simulator/sim-node";
import {
  ASYNC_ONLY,
  type EdgeData,
  type FlowEdge,
  type FlowNode,
  type NodeType,
} from "@/lib/simulator";

const nodeTypes = { sim: SimNode };
const POPOVER_SIZE = 260; // keeps the edge popover inside the canvas

const DIRECTIONS: Record<string, string> = {
  up: "вверх",
  down: "вниз",
  left: "влево",
  right: "вправо",
};
const ARIA_LABELS: ReactFlowProps["ariaLabelConfig"] = {
  "node.a11yDescription.default":
    "Enter или пробел выделяют узел, Delete удаляет его, Escape снимает выделение.",
  "node.a11yDescription.keyboardDisabled":
    "Enter или пробел выделяют узел, стрелки двигают его, Delete удаляет, Escape снимает выделение.",
  "node.a11yDescription.ariaLiveMessage": ({ direction, x, y }) =>
    `Узел сдвинут ${DIRECTIONS[direction] ?? direction}, позиция x: ${x}, y: ${y}`,
  "edge.a11yDescription.default":
    "Enter или пробел выделяют связь, Delete удаляет её, Escape снимает выделение.",
  "controls.ariaLabel": "Масштаб",
  "controls.zoomIn.ariaLabel": "Приблизить",
  "controls.zoomOut.ariaLabel": "Отдалить",
  "controls.fitView.ariaLabel": "Показать всю схему",
  "handle.ariaLabel": "Порт",
};

type Props = Pick<
  ReactFlowProps<FlowNode, FlowEdge>,
  | "onNodesChange"
  | "onEdgesChange"
  | "onConnect"
  | "isValidConnection"
  | "onBeforeDelete"
  | "onNodeDragStart"
> & {
  nodes: FlowNode[];
  edges: FlowEdge[];
  // without them the scheme is read-only: an attempt is shown
  onDropType?: (type: NodeType, at: XYPosition) => void;
  onEdgeData?: (id: string, data: EdgeData) => void;
};

export function Canvas({ onDropType, onEdgeData, ...flow }: Props) {
  const readOnly = !onDropType || !onEdgeData;
  const { screenToFlowPosition } = useReactFlow();
  const box = useRef<HTMLDivElement>(null);
  const [menu, setMenu] = useState<{ id: string; x: number; y: number }>();
  // gone once the edge is deleted or undone
  const edge = menu && flow.edges.find((e) => e.id === menu.id);
  const target = edge && flow.nodes.find((n) => n.id === edge.target);

  return (
    <div
      ref={box}
      className="relative h-full rounded-lg border"
      onDragOver={(e) => {
        if (readOnly || !e.dataTransfer.types.includes(DRAG_TYPE)) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
      }}
      onDrop={(e) => {
        const type = e.dataTransfer.getData(DRAG_TYPE) as NodeType;
        if (!type || !onDropType) return;
        e.preventDefault();
        onDropType(type, screenToFlowPosition({ x: e.clientX, y: e.clientY }));
      }}
    >
      <ReactFlow
        {...flow}
        nodeTypes={nodeTypes}
        deleteKeyCode={readOnly ? null : ["Delete", "Backspace"]}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={!readOnly}
        ariaLabelConfig={ARIA_LABELS}
        fitView
        fitViewOptions={{ maxZoom: 1 }}
        onEdgeClick={(e, clicked) => {
          if (readOnly) return;
          const r = box.current!.getBoundingClientRect();
          setMenu({
            id: clicked.id,
            x: Math.max(
              0,
              Math.min(e.clientX - r.left, r.width - POPOVER_SIZE),
            ),
            y: Math.max(
              0,
              Math.min(e.clientY - r.top, r.height - POPOVER_SIZE),
            ),
          });
        }}
        onPaneClick={() => setMenu(undefined)}
        onNodeClick={() => setMenu(undefined)}
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
      {flow.nodes.length === 0 && (
        <p className="pointer-events-none absolute inset-0 grid place-items-center p-6 text-center text-muted-foreground">
          Добавь User и опиши, куда идут запросы
        </p>
      )}
      {menu && edge && target && onEdgeData && (
        <EdgePopover
          edge={edge}
          asyncOnly={ASYNC_ONLY.has(target.data.type)}
          x={menu.x}
          y={menu.y}
          onChange={(data) => onEdgeData(edge.id, data)}
          onClose={() => setMenu(undefined)}
        />
      )}
    </div>
  );
}

import { Button } from "@/components/ui/button";
import { MAX_NODES, type Component, type NodeType } from "@/lib/simulator";

// The drag payload of a palette button: the node type.
export const DRAG_TYPE = "application/x-devplus-sim-node";

// A click or Enter puts the component in the middle of the canvas; dragging puts it under the cursor.
export function Palette({
  catalog,
  full,
  hasUser,
  onAdd,
}: {
  catalog: Component[];
  full: boolean;
  hasUser: boolean;
  onAdd: (type: NodeType) => void;
}) {
  return (
    <section aria-labelledby="sim-palette-h">
      <h2 id="sim-palette-h" className="mb-2 text-sm font-semibold">
        Компоненты
      </h2>
      <ul className="grid gap-1.5">
        {catalog.map((c) => (
          <li key={c.type}>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full justify-start"
              title={c.description}
              draggable
              disabled={full || (c.type === "User" && hasUser)}
              onDragStart={(e) => {
                e.dataTransfer.setData(DRAG_TYPE, c.type);
                e.dataTransfer.effectAllowed = "move";
              }}
              onClick={() => onAdd(c.type)}
            >
              {c.label}
            </Button>
          </li>
        ))}
      </ul>
      {full && (
        <p className="mt-2 text-xs text-muted-foreground">
          На схеме не больше {MAX_NODES} узлов.
        </p>
      )}
    </section>
  );
}

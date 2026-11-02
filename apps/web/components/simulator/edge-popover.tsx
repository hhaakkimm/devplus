import { ParamField } from "@/components/simulator/inspector";
import { Button } from "@/components/ui/button";
import { RATIO, type EdgeData, type FlowEdge } from "@/lib/simulator";

const KINDS = [
  ["sync", "sync: ждёт ответа"],
  ["async", "async: не ждёт ответа"],
] as const;

export function EdgePopover({
  edge,
  asyncOnly,
  x,
  y,
  onChange,
  onClose,
}: {
  edge: FlowEdge;
  asyncOnly: boolean; // edges into a queue or a worker are always async
  x: number;
  y: number;
  onChange: (data: EdgeData) => void;
  onClose: () => void;
}) {
  const title = `Связь ${edge.source} → ${edge.target}`;
  return (
    <div
      role="dialog"
      aria-label={title}
      style={{ left: x, top: y }}
      className="absolute z-10 grid w-60 gap-3 rounded-lg border bg-background p-3 text-sm shadow-md"
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <p className="font-medium">{title}</p>
      <fieldset className="grid gap-1">
        <legend className="mb-1 font-medium">Вызов</legend>
        {KINDS.map(([kind, label]) => (
          <label key={kind} className="flex items-center gap-2">
            <input
              type="radio"
              name={`kind-${edge.id}`}
              value={kind}
              checked={edge.data.kind === kind}
              disabled={asyncOnly && kind === "sync"}
              onChange={() => onChange({ ...edge.data, kind })}
            />
            {label}
          </label>
        ))}
        {asyncOnly && (
          <p className="text-xs text-muted-foreground">
            В очередь и воркер связь всегда async.
          </p>
        )}
      </fieldset>
      <ParamField
        key={edge.id}
        param={RATIO}
        value={edge.data.ratio}
        onChange={(ratio) => onChange({ ...edge.data, ratio })}
      />
      <Button type="button" variant="outline" size="sm" onClick={onClose}>
        Закрыть
      </Button>
    </div>
  );
}

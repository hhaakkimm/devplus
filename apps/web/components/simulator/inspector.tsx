import { useId, useState } from "react";
import { Input } from "@/components/ui/input";
import {
  paramError,
  type Component,
  type FlowNode,
  type Param,
} from "@/lib/simulator";

// A number within the param's limits; the text being typed is kept until it is a valid value,
// only valid values reach `onChange`.
export function ParamField({
  param,
  value,
  onChange,
}: {
  param: Param;
  value: number;
  onChange: (value: number) => void;
}) {
  const id = useId();
  const [text, setText] = useState(String(value));
  const [seen, setSeen] = useState(value);
  // an undo replaces what is typed, unless the text already says that number ("0.50" for 0.5)
  if (value !== seen) {
    setSeen(value);
    if (Number(text) !== value) setText(String(value));
  }
  const error =
    text.trim() === "" ? "Введите число" : paramError(param, Number(text));

  return (
    <div className="grid gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {param.label}
      </label>
      <Input
        id={id}
        type="number"
        inputMode={param.kind === "int" ? "numeric" : "decimal"}
        min={param.min}
        max={param.max}
        step={param.kind === "int" ? 1 : 0.01}
        value={text}
        aria-invalid={error ? true : undefined}
        aria-describedby={`${id}-hint`}
        onChange={(e) => {
          const next = e.target.value;
          setText(next);
          const v = Number(next);
          if (next.trim() !== "" && !paramError(param, v)) onChange(v);
        }}
      />
      <p
        id={`${id}-hint`}
        className={`text-xs ${error ? "text-destructive" : "text-muted-foreground"}`}
      >
        {error ??
          `${param.help} От ${param.min} до ${param.max}${param.kind === "int" ? ", целое" : ""}.`}
      </p>
    </div>
  );
}

export function Inspector({
  node,
  spec,
  onParam,
}: {
  node?: FlowNode;
  spec?: Component;
  onParam: (key: string, value: number) => void;
}) {
  return (
    <section aria-labelledby="sim-inspector-h">
      <h2 id="sim-inspector-h" className="mb-2 text-sm font-semibold">
        Инспектор
      </h2>
      {!node || !spec ? (
        <p className="text-sm text-muted-foreground">Выбери узел на схеме.</p>
      ) : (
        <div className="grid gap-3">
          <div>
            <p className="font-medium">{spec.label}</p>
            <p className="text-xs text-muted-foreground">{node.id}</p>
          </div>
          <p className="text-xs text-muted-foreground">{spec.description}</p>
          {spec.params.length === 0 && (
            <p className="text-sm text-muted-foreground">Параметров нет.</p>
          )}
          {spec.params.map((p) => (
            <ParamField
              // a new node starts from its own value, not from the text typed for the previous one
              key={`${node.id}:${p.key}`}
              param={p}
              value={node.data.params[p.key]}
              onChange={(v) => onParam(p.key, v)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

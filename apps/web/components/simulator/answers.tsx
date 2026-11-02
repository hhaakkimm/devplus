import { useId } from "react";
import { Textarea } from "@/components/ui/textarea";
import { MAX_ANSWER_CHARS, type Answers as Values } from "@/lib/simulator";

const FIELDS: [keyof Values, string][] = [
  ["requirements", "Требования и допущения"],
  ["estimates", "Оценка нагрузки"],
  ["tradeoffs", "Ключевые решения и компромиссы"],
];

// The three written answers; read-only while an attempt is shown.
export function Answers({
  answers,
  onChange,
}: {
  answers: Values;
  onChange?: (answers: Values) => void;
}) {
  const id = useId();
  return (
    <div className="grid gap-4">
      {FIELDS.map(([key, label]) => (
        <div key={key} className="grid gap-1.5">
          <label htmlFor={`${id}-${key}`} className="text-sm font-medium">
            {label}
          </label>
          <Textarea
            id={`${id}-${key}`}
            rows={6}
            maxLength={MAX_ANSWER_CHARS}
            readOnly={!onChange}
            value={answers[key]}
            onChange={(e) => onChange?.({ ...answers, [key]: e.target.value })}
          />
          <p className="text-right text-xs text-muted-foreground">
            {answers[key].length} / {MAX_ANSWER_CHARS}
          </p>
        </div>
      ))}
    </div>
  );
}

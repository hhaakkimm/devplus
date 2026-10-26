"use client";

import { useId, useRef, useState } from "react";
import { ErrorList, Field, selectClass } from "@/components/lab/form-parts";
import { GradersField } from "@/components/lab/graders-field";
import { type Result, useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { buildGraders, type Grader, type GraderRow } from "@/lib/graders";
import { money } from "@/lib/runs";

export type RunBody = {
  dataset_id: string;
  graders: Grader[];
  cost_limit_usd?: string | null;
};

type Estimate = { estimated_cost_usd: string; cost_limit_usd: string };

// A button and a dialog that ask for a dataset and graders and hand them to `submit`.
// With `estimate` the dialog also has a cost limit and a cost estimate (a Lab run has both).
export function RunDialog<T>({
  label,
  submitLabel,
  note,
  datasets,
  disabled,
  estimate,
  submit,
  onDone,
}: {
  label: string; // the button and the title of the dialog
  submitLabel: string;
  note?: string;
  datasets: { id: string; name: string; case_count: number }[];
  disabled?: boolean;
  estimate?: (body: RunBody) => Promise<Result<Estimate>>;
  submit: (body: RunBody) => Promise<Result<T>>;
  onDone: (data: T) => void;
}) {
  const titleId = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const form = useRef<HTMLFormElement>(null);
  const [rows, setRows] = useState<GraderRow[]>([]);
  const [estimated, setEstimated] = useState<string | null>(null);
  const { busy, error, setError, run } = useAction();

  const edit = () => {
    setEstimated(null);
    setError(null);
  };

  // The request body, or null after showing why the form is not ready.
  function body(): RunBody | null {
    const f = form.current!;
    if (!f.reportValidity()) return null;
    const data = new FormData(f);
    const built = buildGraders(rows, data);
    if ("error" in built) {
      setError(built.error);
      return null;
    }
    const limit = String(data.get("limit") ?? "").trim();
    return {
      dataset_id: String(data.get("dataset")),
      graders: built.graders,
      ...(estimate && { cost_limit_usd: limit || null }),
    };
  }

  function estimateCost() {
    const b = body();
    if (!b || !estimate) return;
    run<Estimate>(
      () => estimate(b),
      (r) =>
        setEstimated(
          `Ожидаемая стоимость: ${money(r.estimated_cost_usd)} (лимит ${money(r.cost_limit_usd, 2)})`,
        ),
    );
  }

  function send(e: React.FormEvent) {
    e.preventDefault();
    const b = body();
    if (b) run<T>(() => submit(b), onDone);
  }

  return (
    <>
      <Button onClick={() => dialog.current?.showModal()} disabled={disabled}>
        {label}
      </Button>
      <dialog
        ref={dialog}
        aria-labelledby={titleId}
        className="m-auto max-h-[90vh] w-[min(40rem,calc(100vw-2rem))] overflow-auto rounded-lg border bg-background p-6 text-foreground backdrop:bg-black/50"
      >
        <h2 id={titleId} className="text-xl font-semibold">
          {label}
        </h2>
        {note && <p className="mt-1 text-sm text-muted-foreground">{note}</p>}
        <form
          ref={form}
          onSubmit={send}
          onChange={edit}
          className="mt-4 grid gap-4"
        >
          <Field label="Датасет">
            <select
              name="dataset"
              required
              defaultValue=""
              className={selectClass}
            >
              <option value="" disabled>
                Выберите датасет
              </option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} (кейсов: {d.case_count})
                </option>
              ))}
            </select>
          </Field>
          <GradersField
            rows={rows}
            onChange={(next) => {
              setRows(next);
              edit();
            }}
          />
          {estimate && (
            <Field label="Лимит, $" hint="Пусто: лимит по умолчанию">
              <Input name="limit" type="number" min={0} step="any" />
            </Field>
          )}
          {estimated && (
            <p role="status" className="text-sm">
              {estimated}
            </p>
          )}
          <ErrorList messages={error ? [error] : []} />
          <div className="flex flex-wrap gap-2">
            {estimate && (
              <Button variant="outline" onClick={estimateCost} disabled={busy}>
                Оценить стоимость
              </Button>
            )}
            <Button type="submit" disabled={busy}>
              {submitLabel}
            </Button>
            <Button variant="ghost" onClick={() => dialog.current?.close()}>
              Отмена
            </Button>
          </div>
        </form>
      </dialog>
    </>
  );
}

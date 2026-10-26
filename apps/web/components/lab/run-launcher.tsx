"use client";

import { useRef, useState } from "react";
import { ErrorList, Field, selectClass } from "@/components/lab/form-parts";
import { GradersField } from "@/components/lab/graders-field";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { browserApi } from "@/lib/browser-api";
import { buildGraders, type GraderRow } from "@/lib/graders";
import { money } from "@/lib/runs";

// Runs the latest version of the prompt.
// shortcut: no version picker, a run of an older version is not possible; add a select when needed
export function RunLauncher({
  versionId,
  versionNumber,
  datasets,
}: {
  versionId: string;
  versionNumber: number;
  datasets: { id: string; name: string; case_count: number }[];
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const form = useRef<HTMLFormElement>(null);
  const [rows, setRows] = useState<GraderRow[]>([]);
  const [estimate, setEstimate] = useState<string | null>(null);
  const { busy, error, setError, run, router } = useAction();

  const edit = () => {
    setEstimate(null);
    setError(null);
  };

  // The request body, or null after showing why the form is not ready.
  function body() {
    const f = form.current!;
    if (!f.reportValidity()) return null;
    const data = new FormData(f);
    const built = buildGraders(rows, data);
    if ("error" in built) {
      setError(built.error);
      return null;
    }
    const limit = String(data.get("limit")).trim();
    return {
      prompt_version_id: versionId,
      dataset_id: String(data.get("dataset")),
      graders: built.graders,
      cost_limit_usd: limit || null,
    };
  }

  function estimateCost() {
    const b = body();
    if (!b) return;
    run<{ estimated_cost_usd: string; cost_limit_usd: string }>(
      () => browserApi.POST("/api/evals/runs/estimate", { body: b }),
      (r) =>
        setEstimate(
          `Ожидаемая стоимость: ${money(r.estimated_cost_usd)} (лимит ${money(r.cost_limit_usd, 2)})`,
        ),
    );
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const b = body();
    if (!b) return;
    run<{ id: string }>(
      () => browserApi.POST("/api/evals/runs", { body: b }),
      (created) => router.push(`/lab/runs/${created.id}`),
    );
  }

  return (
    <>
      <Button onClick={() => dialog.current?.showModal()}>
        Запустить прогон
      </Button>
      <dialog
        ref={dialog}
        aria-labelledby="run-launcher-title"
        className="m-auto max-h-[90vh] w-[min(40rem,calc(100vw-2rem))] overflow-auto rounded-lg border bg-background p-6 text-foreground backdrop:bg-black/50"
      >
        <h2 id="run-launcher-title" className="text-xl font-semibold">
          Запустить прогон
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Версия {versionNumber}
        </p>
        <form
          ref={form}
          onSubmit={submit}
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
          <Field label="Лимит, $" hint="Пусто: лимит по умолчанию">
            <Input name="limit" type="number" min={0} step="any" />
          </Field>
          {estimate && (
            <p role="status" className="text-sm">
              {estimate}
            </p>
          )}
          <ErrorList messages={error ? [error] : []} />
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={estimateCost} disabled={busy}>
              Оценить стоимость
            </Button>
            <Button type="submit" disabled={busy}>
              Запустить
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

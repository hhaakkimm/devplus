"use client";

import { ErrorList, Field } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { browserApi } from "@/lib/browser-api";
import { checkCase } from "@/lib/jsonl";

export function AddCaseForm({ datasetId }: { datasetId: string }) {
  const { busy, error, setError, run, router } = useAction();

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    let variables: unknown;
    try {
      variables = JSON.parse(String(f.get("variables")));
    } catch {
      return setError("Переменные: некорректный JSON");
    }
    const expected = String(f.get("expected"));
    const checked = checkCase({ variables, expected: expected || null });
    if (typeof checked === "string") return setError(checked);
    run(
      () =>
        browserApi.POST("/api/evals/datasets/{dataset_id}/cases", {
          params: { path: { dataset_id: datasetId } },
          body: checked,
        }),
      () => {
        form.reset();
        router.refresh();
      },
    );
  }

  return (
    <form onSubmit={submit} className="grid gap-4">
      <Field label="Переменные (JSON-объект)">
        <Textarea
          name="variables"
          required
          rows={3}
          placeholder='{"text": "..."}'
          className="font-mono"
        />
      </Field>
      <Field label="Эталон (необязательно)">
        <Input name="expected" />
      </Field>
      <ErrorList messages={error ? [error] : []} />
      <div>
        <Button type="submit" disabled={busy}>
          Добавить кейс
        </Button>
      </div>
    </form>
  );
}

"use client";

import { ErrorList, Field } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { browserApi } from "@/lib/browser-api";

export function NewDatasetForm() {
  const { busy, error, run, router } = useAction();

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const name = String(new FormData(e.currentTarget).get("name"));
    run(
      () => browserApi.POST("/api/evals/datasets", { body: { name } }),
      (dataset) => router.push(`/lab/datasets/${dataset.id}`),
    );
  }

  return (
    <form onSubmit={submit} className="grid max-w-md gap-4">
      <Field label="Название">
        <Input name="name" required maxLength={200} />
      </Field>
      <ErrorList messages={error ? [error] : []} />
      <div>
        <Button type="submit" disabled={busy}>
          Создать датасет
        </Button>
      </div>
    </form>
  );
}

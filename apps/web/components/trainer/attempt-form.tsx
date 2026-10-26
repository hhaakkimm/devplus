"use client";

import { ErrorList, Field } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { browserApi } from "@/lib/browser-api";

// The model, effort and token limit are the task's: the user writes only the two texts.
export function AttemptForm({
  module: moduleSlug,
  task,
  model,
  effort,
}: {
  module: string;
  task: string;
  model: string;
  effort: string;
}) {
  const { busy, error, run } = useAction();

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    // the page is refreshed with the new attempt, which polls until it has a verdict
    run(() =>
      browserApi.POST("/api/trainer/tasks/{module}/{task}/attempts", {
        params: { path: { module: moduleSlug, task } },
        body: {
          system: String(f.get("system")),
          user_template: String(f.get("user_template")),
        },
      }),
    );
  }

  return (
    <form onSubmit={submit} className="grid gap-4">
      <Field label="Системный промпт">
        <Textarea name="system" rows={6} className="font-mono" />
      </Field>
      <Field label="Шаблон сообщения">
        <Textarea
          name="user_template"
          rows={6}
          required
          className="font-mono"
        />
      </Field>
      <p className="text-sm text-muted-foreground">
        Модель: {model} · effort: {effort}
      </p>
      <ErrorList messages={error ? [error] : []} />
      <div>
        <Button type="submit" disabled={busy}>
          Отправить
        </Button>
      </div>
    </form>
  );
}

"use client";

import type { components } from "@devplus/api-client";
import { useState } from "react";
import { Field, ErrorList } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { browserApi } from "@/lib/browser-api";
import { templateVariables } from "@/lib/template";

type VersionIn = components["schemas"]["VersionIn"];

const MODELS: VersionIn["model"][] = [
  "claude-opus-5-5",
  "claude-sonnet-5-5",
  "claude-haiku-5-5",
];
const EFFORTS: NonNullable<VersionIn["effort"]>[] = [
  "low",
  "medium",
  "high",
  "xhigh",
  "max",
];

const selectClass =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30";

// Without `promptId` it creates a prompt (and asks for a name), with it adds a version.
export function PromptForm({
  promptId,
  initial,
}: {
  promptId?: string;
  initial?: components["schemas"]["VersionOut"];
}) {
  const { busy, error, setError, run, router } = useAction();
  const [template, setTemplate] = useState(initial?.user_template ?? "");
  const variables = templateVariables(template);

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const schemaText = String(f.get("output_schema")).trim();
    let output_schema: VersionIn["output_schema"] = null;
    if (schemaText) {
      try {
        output_schema = JSON.parse(schemaText);
      } catch {
        return setError("JSON-схема ответа: некорректный JSON");
      }
      if (
        output_schema === null ||
        typeof output_schema !== "object" ||
        Array.isArray(output_schema)
      ) {
        return setError("JSON-схема ответа: ожидается JSON-объект");
      }
    }
    const version: VersionIn = {
      system: String(f.get("system")),
      user_template: template,
      model: String(f.get("model")) as VersionIn["model"],
      effort: String(f.get("effort")) as VersionIn["effort"],
      max_tokens: Number(f.get("max_tokens")),
      output_schema,
    };
    if (promptId) {
      run(() =>
        browserApi.POST("/api/evals/prompts/{prompt_id}/versions", {
          params: { path: { prompt_id: promptId } },
          body: version,
        }),
      );
    } else {
      run(
        () =>
          browserApi.POST("/api/evals/prompts", {
            body: { name: String(f.get("name")), version },
          }),
        (prompt) => router.push(`/lab/prompts/${prompt.id}`),
      );
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4">
      {!promptId && (
        <Field label="Название">
          <Input name="name" required maxLength={200} />
        </Field>
      )}
      <Field label="Системный промпт">
        <Textarea
          name="system"
          rows={6}
          defaultValue={initial?.system}
          className="font-mono"
        />
      </Field>
      <Field
        label="Шаблон сообщения"
        hint={`Переменные: ${variables.join(", ") || "нет"}`}
      >
        <Textarea
          name="user_template"
          rows={6}
          value={template}
          onChange={(e) => setTemplate(e.target.value)}
          className="font-mono"
        />
      </Field>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Модель">
          <select
            name="model"
            defaultValue={initial?.model ?? "claude-sonnet-5-5"}
            className={selectClass}
          >
            {MODELS.map((m) => (
              <option key={m}>{m}</option>
            ))}
          </select>
        </Field>
        <Field label="Effort">
          <select
            name="effort"
            defaultValue={initial?.effort ?? "medium"}
            className={selectClass}
          >
            {EFFORTS.map((e) => (
              <option key={e}>{e}</option>
            ))}
          </select>
        </Field>
        <Field label="Макс. токенов">
          <Input
            name="max_tokens"
            type="number"
            required
            min={1}
            max={16000}
            defaultValue={initial?.max_tokens ?? 1024}
          />
        </Field>
      </div>
      <Field label="JSON-схема ответа (необязательно)">
        <Textarea
          name="output_schema"
          rows={4}
          defaultValue={
            initial?.output_schema
              ? JSON.stringify(initial.output_schema, null, 2)
              : ""
          }
          className="font-mono"
        />
      </Field>
      <ErrorList messages={error ? [error] : []} />
      <div>
        <Button type="submit" disabled={busy}>
          {promptId ? "Сохранить как новую версию" : "Создать промпт"}
        </Button>
      </div>
    </form>
  );
}

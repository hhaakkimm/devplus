"use client";

import type { components } from "@devplus/api-client";
import { useState } from "react";
import { ErrorList, Field, selectClass } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { browserApi } from "@/lib/browser-api";

type Prompt = components["schemas"]["PromptSummaryOut"];
type Mode = "text" | "version";

const MODES: [Mode, string][] = [
  ["text", "Вставить текст"],
  ["version", "Выбрать версию"],
];

// Reviews pasted text or a version of a prompt from the Lab; the result is a page of its own.
export function ReviewForm({
  prompts,
  login,
}: {
  prompts: Prompt[];
  login: string;
}) {
  const { busy, error, run, router } = useAction();
  const [mode, setMode] = useState<Mode>("text");
  const [versions, setVersions] = useState<{ id: string; number: number }[]>(
    [],
  );

  // Versions come with the prompt, not with the list of prompts.
  function pickPrompt(id: string) {
    setVersions([]);
    if (!id) return;
    run(
      () =>
        browserApi.GET("/api/evals/prompts/{prompt_id}", {
          params: { path: { prompt_id: id } },
        }),
      (prompt) => setVersions([...prompt.versions].reverse()),
    );
  }

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body =
      mode === "text"
        ? {
            system: String(f.get("system")),
            user_template: String(f.get("user_template")),
          }
        : { prompt_version_id: String(f.get("version")) };
    run<{ id: string }>(
      () => browserApi.POST("/api/review", { body }),
      (review) => router.push(`/review/${review.id}`),
    );
  }

  return (
    <form onSubmit={submit} className="grid gap-4">
      <fieldset className="flex flex-wrap gap-x-6 gap-y-2">
        <legend className="mb-1 text-sm font-medium">Что разобрать</legend>
        {MODES.map(([value, label]) => (
          <label key={value} className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="mode"
              value={value}
              checked={mode === value}
              onChange={() => setMode(value)}
            />
            {label}
          </label>
        ))}
      </fieldset>
      {/* hidden, not removed: switching the mode must not lose the text */}
      <div hidden={mode !== "text"} className="grid gap-4">
        <Field label="Системный промпт">
          <Textarea name="system" rows={6} className="font-mono" />
        </Field>
        <Field
          label="Шаблон сообщения"
          hint="Системный промпт и шаблон вместе до 20 000 символов"
        >
          <Textarea name="user_template" rows={6} className="font-mono" />
        </Field>
      </div>
      {mode === "version" && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Промпт">
            <select
              required
              defaultValue=""
              disabled={busy}
              onChange={(e) => pickPrompt(e.target.value)}
              className={selectClass}
            >
              <option value="" disabled>
                Выберите промпт
              </option>
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                  {p.owner_login !== login && ` (автор: ${p.owner_login})`}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Версия">
            <select name="version" required className={selectClass}>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  Версия {v.number}
                </option>
              ))}
            </select>
          </Field>
        </div>
      )}
      <ErrorList messages={error ? [error] : []} />
      <div className="flex flex-wrap items-center gap-4">
        <Button type="submit" disabled={busy}>
          Разобрать
        </Button>
        <p className="text-sm text-muted-foreground">
          Разбор занимает около минуты.
        </p>
      </div>
    </form>
  );
}

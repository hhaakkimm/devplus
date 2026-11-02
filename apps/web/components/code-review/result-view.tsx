"use client";

import { useState } from "react";
import { ErrorList, selectClass } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { browserApi } from "@/lib/browser-api";
import type { ReviewAttempt as Attempt } from "@/lib/code-review";

const VERDICT_TEXT: Record<string, string> = {
  approve: "approve",
  request_changes: "request changes",
};

const where = (file: string, [a, b]: number[]) =>
  `${file}:${a === b ? a : `${a}–${b}`}`;

function Badge({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${ok ? "bg-green-600/15 text-green-700 dark:text-green-400" : "bg-destructive/15 text-destructive"}`}
    >
      {children}
    </span>
  );
}

function ReportForm({ id, sections }: { id: string; sections: string[] }) {
  const { busy, error, run } = useAction();
  const [sent, setSent] = useState(false);
  if (sent)
    return (
      <p role="status" className="text-sm">
        Спасибо, жалоба отправлена.
      </p>
    );
  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const section = String(f.get("section") ?? "");
    run(
      () =>
        browserApi.POST("/api/code-review/attempts/{attempt_id}/report", {
          params: { path: { attempt_id: id } },
          body: { text: String(f.get("text")), section: section || null },
        }),
      () => setSent(true),
    );
  }
  return (
    <details>
      <summary className="cursor-pointer text-sm font-medium">
        Сообщить о плохом разборе
      </summary>
      <form onSubmit={submit} className="mt-3 grid gap-3">
        <label className="grid gap-1.5 text-sm font-medium">
          Раздел (необязательно)
          <select name="section" className={selectClass} defaultValue="">
            <option value="">Весь разбор</option>
            {sections.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label className="grid gap-1.5 text-sm font-medium">
          Что не так
          <Textarea name="text" rows={4} required maxLength={2000} />
        </label>
        <ErrorList messages={error ? [error] : []} />
        <div>
          <Button type="submit" disabled={busy}>
            Отправить жалобу
          </Button>
        </div>
      </form>
    </details>
  );
}

// The review after grading: what was found and missed, the traps, the judge's sections and a report form.
export function ResultView({ attempt }: { attempt: Attempt }) {
  const { result, revealed } = attempt;
  if (!result || !revealed) return null;
  const sections = [
    ...revealed.issues.map((i) => i.id),
    ...result.general.map((g) => g.name),
  ];
  return (
    <div className="grid gap-8">
      <section aria-labelledby="summary-h" className="grid gap-2">
        <h2 id="summary-h" className="text-xl font-semibold">
          Результат
        </h2>
        <p className="flex flex-wrap items-center gap-3">
          <Badge ok={result.passed}>
            {result.passed ? "Зачёт" : "Не зачтено"}
          </Badge>
          <span className="text-2xl font-semibold">
            {Math.round(result.score * 100)}%
          </span>
        </p>
        <p className="text-sm">
          Ваш вердикт: {VERDICT_TEXT[result.verdict] ?? result.verdict}.
          Ожидался: {VERDICT_TEXT[revealed.expected_verdict]}.{" "}
          <Badge ok={result.verdict_matches}>
            {result.verdict_matches ? "совпал" : "не совпал"}
          </Badge>
        </p>
        {result.comment && (
          <p className="break-words whitespace-pre-wrap">{result.comment}</p>
        )}
      </section>

      <section aria-labelledby="issues-h">
        <h2 id="issues-h" className="text-xl font-semibold">
          Проблемы в коде
        </h2>
        <ul className="mt-3 space-y-3">
          {revealed.issues.map((i) => (
            <li key={i.id} className="rounded-lg border p-3">
              <p className="flex flex-wrap items-center gap-2">
                <Badge ok={i.found}>{i.found ? "найдена" : "пропущена"}</Badge>
                {i.critical && (
                  <span className="text-xs font-medium text-destructive">
                    критичная
                  </span>
                )}
                <span className="font-mono text-sm">
                  {where(i.file, i.lines)}
                </span>
              </p>
              <p className="mt-2 break-words whitespace-pre-wrap">
                {i.description}
              </p>
              <p className="mt-1 text-sm break-words whitespace-pre-wrap text-muted-foreground">
                {i.reason}
              </p>
            </li>
          ))}
        </ul>
      </section>

      {revealed.traps.length > 0 && (
        <section aria-labelledby="traps-h">
          <h2 id="traps-h" className="text-xl font-semibold">
            Ловушки: код, который выглядит подозрительно, но верен
          </h2>
          <ul className="mt-3 space-y-3">
            {revealed.traps.map((t) => (
              <li
                key={`${t.file}:${t.lines}`}
                className="rounded-lg border p-3"
              >
                <p className="font-mono text-sm">{where(t.file, t.lines)}</p>
                <p className="mt-1 break-words whitespace-pre-wrap">
                  {t.why_fine}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="general-h">
        <h2 id="general-h" className="text-xl font-semibold">
          Общая оценка
        </h2>
        <ul className="mt-3 space-y-3">
          {result.general.map((g) => (
            <li key={g.name}>
              <p className="font-medium">
                {g.name}: {g.score} из 5
              </p>
              <p className="text-sm break-words whitespace-pre-wrap text-muted-foreground">
                {g.reason}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <ReportForm id={attempt.id} sections={sections} />
    </div>
  );
}

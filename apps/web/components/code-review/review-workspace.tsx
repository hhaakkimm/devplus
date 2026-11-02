"use client";

import { useEffect, useRef, useState } from "react";
import { CodeViewer } from "@/components/code-review/code-viewer";
import { CommentForm } from "@/components/code-review/comment-form";
import { CommentList } from "@/components/code-review/comment-list";
import { ErrorList } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { apiDetail, browserApi, SIGN_IN_URL } from "@/lib/browser-api";
import type {
  HighlightedFile,
  ReviewAttempt as Attempt,
  ReviewTask as Task,
} from "@/lib/code-review";
import {
  addComment,
  canSubmit,
  commentError,
  MAX_SUMMARY_CHARS,
  nextSelection,
  removeComment,
  updateComment,
  type DraftComment,
  type Selection,
  type Verdict,
} from "@/lib/code-review-state";

type Draft = {
  comments: DraftComment[];
  verdict: Verdict | null;
  summary: string;
};
type Saving = "saved" | "saving" | "error";

const DEBOUNCE_MS = 800;
const SAVING_TEXT: Record<Saving, string> = {
  saved: "Сохранено",
  saving: "Сохраняю…",
  error: "Не удалось сохранить",
};
const VERDICTS: [Verdict, string][] = [
  ["approve", "Принять (approve)"],
  ["request_changes", "Запросить правки (request changes)"],
];

// A draft is edited and autosaved; a failed attempt shows the same work read-only with a resend button.
export function ReviewWorkspace({
  task,
  highlighted,
  attempt,
}: {
  task: Task;
  highlighted: HighlightedFile[];
  attempt: Attempt;
}) {
  const readOnly = attempt.status !== "draft";
  const { busy, error, setError, run, router } = useAction();
  const [draft, setDraft] = useState<Draft>({
    comments: attempt.comments,
    verdict: (attempt.verdict as Verdict | null) ?? null,
    summary: attempt.summary ?? "",
  });
  const [active, setActive] = useState(highlighted[0].path);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [saving, setSaving] = useState<Saving>("saved");
  const lineCounts = Object.fromEntries(
    highlighted.map((f) => [f.path, f.lines.length]),
  );

  // Saves run one at a time and always send the newest draft, so an older answer can neither
  // overwrite newer work on the server nor set the indicator.
  const latest = useRef(draft);
  const dirty = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const chain = useRef<Promise<boolean>>(Promise.resolve(true));

  function save(): Promise<boolean> {
    clearTimeout(timer.current);
    const next = chain.current.then(async () => {
      if (!dirty.current) return true;
      dirty.current = false;
      setSaving("saving");
      try {
        const { error, response } = await browserApi.PUT(
          "/api/code-review/attempts/{attempt_id}",
          {
            params: { path: { attempt_id: attempt.id } },
            body: latest.current,
          },
        );
        if (response.ok) {
          if (!dirty.current) setSaving("saved");
          return true;
        }
        if (response.status === 401) window.location.assign(SIGN_IN_URL);
        else if (response.status === 409)
          router.refresh(); // no longer a draft
        else console.warn("save failed:", apiDetail(error, response.status));
      } catch {
        // offline: keep the draft dirty for the next try
      }
      dirty.current = true;
      setSaving("error");
      return false;
    });
    chain.current = next;
    return next;
  }

  function change(patch: Partial<Draft>) {
    latest.current = { ...latest.current, ...patch };
    setDraft(latest.current);
    dirty.current = true;
    setSaving("saving");
    clearTimeout(timer.current);
    timer.current = setTimeout(save, DEBOUNCE_MS);
  }

  // shortcut: only a leaving page saves its last edit; closing the tab loses up to 800 ms of typing
  useEffect(
    () => () => {
      if (dirty.current) void save();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  function add(text: string): string | null {
    if (!selection) return null;
    const c = {
      file: selection.file,
      line_start: selection.range[0],
      line_end: selection.range[1],
      text: text.trim(),
    };
    const problem = commentError(c, lineCounts, draft.comments.length);
    if (problem) return problem;
    change({ comments: addComment(draft.comments, c) });
    setSelection(null);
    return null;
  }

  async function submit() {
    if (!readOnly && !(await save())) {
      setError("Не удалось сохранить черновик, попробуйте ещё раз");
      return;
    }
    run(async () => {
      const res = await browserApi.POST(
        "/api/code-review/attempts/{attempt_id}/submit",
        { params: { path: { attempt_id: attempt.id } } },
      );
      // the judge failed or the attempt was sent elsewhere: the page shows the new state
      if (res.response.status === 409 || res.response.status >= 500)
        router.refresh();
      return res;
    });
  }

  const wide = (
    <div
      role="group"
      aria-label={`Ревью: ${task.title}`}
      className="hidden lg:block"
    >
      {readOnly && attempt.error && (
        <p role="alert" className="mb-3 text-sm text-destructive">
          Разбор не удался: {attempt.error}. Замечания сохранены, можно
          отправить снова.
        </p>
      )}
      <div className="grid grid-cols-[14rem_minmax(0,1fr)_20rem] gap-4">
        <CodeViewer
          files={highlighted}
          active={active}
          onOpen={setActive}
          comments={draft.comments}
          selection={selection}
          onSelect={
            readOnly
              ? undefined
              : (file, line, shift) =>
                  setSelection((s) => nextSelection(s, file, line, shift))
          }
        />
        <section aria-labelledby="comments-h">
          <h2 id="comments-h" className="mb-2 text-lg font-semibold">
            Замечания ({draft.comments.length})
          </h2>
          <CommentList
            comments={draft.comments}
            onEdit={
              readOnly
                ? undefined
                : (i, text) =>
                    change({ comments: updateComment(draft.comments, i, text) })
            }
            onRemove={
              readOnly
                ? undefined
                : (i) => change({ comments: removeComment(draft.comments, i) })
            }
          />
        </section>
      </div>
      {selection && !readOnly && (
        <CommentForm
          // a new selection is a new comment: start from an empty field
          key={`${selection.file}:${selection.range}`}
          file={selection.file}
          range={selection.range}
          onAdd={add}
          onCancel={() => setSelection(null)}
        />
      )}
      <div className="mt-6 grid gap-4 border-t pt-4">
        <fieldset disabled={readOnly} className="grid gap-2">
          <legend className="text-sm font-medium">Вердикт</legend>
          {VERDICTS.map(([value, label]) => (
            <label key={value} className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="verdict"
                value={value}
                checked={draft.verdict === value}
                onChange={() => change({ verdict: value })}
              />
              {label}
            </label>
          ))}
        </fieldset>
        <label className="grid gap-1.5 text-sm font-medium">
          Резюме
          <Textarea
            rows={4}
            maxLength={MAX_SUMMARY_CHARS}
            readOnly={readOnly}
            value={draft.summary}
            onChange={(e) => change({ summary: e.target.value })}
          />
        </label>
        <ErrorList messages={error ? [error] : []} />
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            onClick={submit}
            disabled={busy || !canSubmit(draft)}
          >
            {readOnly ? "Отправить снова" : "Отправить"}
          </Button>
          {busy && (
            <span role="status" className="text-sm text-muted-foreground">
              Оцениваю… это займёт до минуты
            </span>
          )}
          {!readOnly && (
            <span
              role="status"
              aria-live="polite"
              className={`text-sm ${saving === "error" ? "text-destructive" : "text-muted-foreground"}`}
            >
              {SAVING_TEXT[saving]}
            </span>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <>
      <p className="rounded-lg border p-4 text-sm text-muted-foreground lg:hidden">
        Откройте задачу на десктопе, чтобы писать замечания
      </p>
      {wide}
    </>
  );
}

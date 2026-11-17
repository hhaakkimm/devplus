"use client";

import { useEffect, useRef, useState } from "react";
import { CodeViewer } from "@/components/code-review/code-viewer";
import { CommentForm } from "@/components/code-review/comment-form";
import { RetryButton } from "@/components/code-review/attempt-actions";
import { CommentList } from "@/components/code-review/comment-list";
import { ErrorList } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { apiDetail, browserApi } from "@/lib/browser-api";
import { signInUrl } from "@/lib/miniapp";
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
  stripIds,
  updateComment,
  withId,
  type KeyedComment,
  type Selection,
  type Verdict,
} from "@/lib/code-review-state";

type Draft = {
  comments: KeyedComment[];
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

// A draft is edited and autosaved; a failed attempt shows the same work read-only with a resend
// and a start-over button; a graded one shows the code and the student's comments read-only.
export function ReviewWorkspace({
  task,
  highlighted,
  attempt,
}: {
  task: Task;
  highlighted: HighlightedFile[];
  attempt: Attempt;
}) {
  const sent = attempt.status !== "draft";
  const graded = attempt.status === "graded";
  const { busy, error, setError, run, router } = useAction();
  // set before the draft is flushed: edits made while the attempt is being sent would be lost
  const [submitting, setSubmitting] = useState(false);
  const readOnly = sent || submitting || busy;
  const [draft, setDraft] = useState<Draft>({
    comments: attempt.comments.map(withId),
    verdict: (attempt.verdict as Verdict | null) ?? null,
    summary: attempt.summary ?? "",
  });
  const [active, setActive] = useState(highlighted[0].path);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [saving, setSaving] = useState<Saving>("saved");
  const [saveDetail, setSaveDetail] = useState("");
  const lineCounts = Object.fromEntries(
    highlighted.map((f) => [f.path, f.lines.length]),
  );

  // Saves run one at a time and always send the newest draft, so an older answer can neither
  // overwrite newer work on the server nor set the indicator.
  const latest = useRef(draft);
  const dirty = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const chain = useRef<Promise<string | null>>(Promise.resolve(null));

  // resolves to null when everything is saved, else to the reason
  function save(): Promise<string | null> {
    clearTimeout(timer.current);
    const next = chain.current.then(async () => {
      if (!dirty.current) return null;
      dirty.current = false;
      setSaving("saving");
      let reason: string;
      try {
        const { error, response } = await browserApi.PUT(
          "/api/code-review/attempts/{attempt_id}",
          {
            params: { path: { attempt_id: attempt.id } },
            body: {
              ...latest.current,
              comments: stripIds(latest.current.comments),
            },
          },
        );
        if (response.ok) {
          if (!dirty.current) setSaving("saved");
          return null;
        }
        reason = apiDetail(error, response.status);
        if (response.status === 401)
          window.location.assign(signInUrl(document.cookie));
        else if (response.status === 409) {
          dirty.current = false; // no longer a draft: the unmount must not send it again
          router.refresh();
          return reason;
        }
      } catch {
        reason = "Нет связи с сервером"; // keep the draft dirty for the next try
      }
      dirty.current = true;
      setSaving("error");
      setSaveDetail(reason);
      return reason;
    });
    chain.current = next;
    return next;
  }

  function change(patch: Partial<Draft>) {
    if (readOnly) return;
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
    change({ comments: addComment(draft.comments, withId(c)) });
    setSelection(null);
    return null;
  }

  async function submit() {
    if (submitting || busy) return;
    setSubmitting(true);
    if (!sent) {
      const reason = await save();
      if (reason) {
        setError(`Не удалось сохранить черновик: ${reason}`);
        setSubmitting(false);
        return;
      }
    }
    await run(async () => {
      const res = await browserApi.POST(
        "/api/code-review/attempts/{attempt_id}/submit",
        { params: { path: { attempt_id: attempt.id } } },
      );
      // the judge failed or the attempt was sent elsewhere: the page shows the new state
      if (res.response.status === 409 || res.response.status >= 500)
        router.refresh();
      return res;
    });
    setSubmitting(false);
  }

  const wide = (
    <div
      role="group"
      aria-label={`Ревью: ${task.title}`}
      className="hidden lg:block"
    >
      {attempt.status === "failed" && (
        <div role="alert" className="mb-3 grid gap-2 text-sm">
          <p className="text-destructive">
            Разбор не удался{attempt.error ? `: ${attempt.error}` : ""}.
            Замечания сохранены, можно отправить снова или начать заново с этим
            же текстом.
          </p>
          <RetryButton
            module={task.module}
            slug={task.slug}
            label="Начать заново"
          />
        </div>
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
          // the key is the file only: Shift+click changes the range of the same comment and must
          // keep the typed text; adding or cancelling closes the form, so the next one starts empty
          key={selection.file}
          file={selection.file}
          range={selection.range}
          onAdd={add}
          onCancel={() => setSelection(null)}
        />
      )}
      {!graded && (
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
              disabled={busy || submitting || !canSubmit(draft)}
            >
              {sent ? "Отправить снова" : "Отправить"}
            </Button>
            {(busy || submitting) && (
              <span role="status" className="text-sm text-muted-foreground">
                Оцениваю… это займёт до минуты
              </span>
            )}
            {!sent && (
              <span
                role="status"
                aria-live="polite"
                className={`text-sm ${saving === "error" ? "text-destructive" : "text-muted-foreground"}`}
              >
                {SAVING_TEXT[saving]}
                {saving === "error" && saveDetail && `: ${saveDetail}`}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {graded ? (
        <div className="lg:hidden">
          <h2 className="mb-2 text-lg font-semibold">
            Замечания ({draft.comments.length})
          </h2>
          <CommentList comments={draft.comments} />
        </div>
      ) : (
        <p className="rounded-lg border p-4 text-sm text-muted-foreground lg:hidden">
          Откройте задачу на десктопе, чтобы писать замечания
        </p>
      )}
      {wide}
    </>
  );
}

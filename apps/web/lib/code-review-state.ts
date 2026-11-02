// Pure state helpers for the review workspace (client-safe). The limits mirror
// apps/api/app/modules/code_review/schemas.py; the API stays the authority.
import { selectionRange, type LineRange } from "@/lib/code-review-lines";

export const MAX_COMMENTS = 50;
export const MAX_COMMENT_CHARS = 2000;
export const MAX_SUMMARY_CHARS = 4000;

export type Verdict = "approve" | "request_changes";
export type DraftComment = {
  file: string;
  line_start: number;
  line_end: number;
  text: string;
};

// The editor and the list need a stable identity per comment: an index changes when an earlier
// comment is deleted. The id lives only on the client; stripIds removes it before the API call.
export type KeyedComment = DraftComment & { id: string };

let lastId = 0;
export const withId = (c: DraftComment): KeyedComment => ({
  ...c,
  id: `c${++lastId}`,
});

export const stripIds = (list: KeyedComment[]): DraftComment[] =>
  list.map(({ file, line_start, line_end, text }) => ({
    file,
    line_start,
    line_end,
    text,
  }));

export function addComment<T extends DraftComment>(list: T[], c: T) {
  return [...list, c];
}

export function updateComment<T extends DraftComment>(
  list: T[],
  i: number,
  text: string,
) {
  return list.map((c, k) => (k === i ? { ...c, text } : c));
}

export function removeComment<T extends DraftComment>(list: T[], i: number) {
  return list.filter((_, k) => k !== i);
}

// `count` is how many comments the draft already holds; `lineCounts` maps a file path to its lines.
export function commentError(
  c: DraftComment,
  lineCounts: Record<string, number>,
  count: number,
): string | null {
  if (count >= MAX_COMMENTS) return `Не больше ${MAX_COMMENTS} замечаний`;
  if (!c.text.trim()) return "Напишите текст замечания";
  if (c.text.length > MAX_COMMENT_CHARS)
    return `Замечание длиннее ${MAX_COMMENT_CHARS} символов`;
  const total = lineCounts[c.file];
  if (total === undefined) return "Файл не найден в задаче";
  if (!(1 <= c.line_start && c.line_start <= c.line_end && c.line_end <= total))
    return `Строки должны лежать в файле (1–${total})`;
  return null;
}

export function canSubmit(d: {
  comments: DraftComment[];
  verdict: Verdict | null;
  summary: string;
}) {
  return (
    d.verdict !== null &&
    d.summary.length <= MAX_SUMMARY_CHARS &&
    (d.comments.length > 0 || d.summary.trim() !== "")
  );
}

export type Selection = { file: string; anchor: number; range: LineRange };

// A click starts a selection on that line; shift-click extends the one in the same file from its anchor.
export function nextSelection(
  sel: Selection | null,
  file: string,
  line: number,
  shift: boolean,
): Selection {
  if (shift && sel && sel.file === file)
    return {
      file,
      anchor: sel.anchor,
      range: selectionRange(sel.anchor, line),
    };
  return { file, anchor: line, range: [line, line] };
}

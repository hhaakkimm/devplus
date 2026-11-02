// Pure line helpers for the code review UI. Numbering must match file_lines in
// apps/api/app/modules/code_review/judge.py, so a range selected here means the same lines there.

export type LineRange = [number, number];

// One trailing newline is dropped, then only "\n" splits: not \r, form feed, \u2028 and the like.
export function splitSourceLines(source: string): string[] {
  return (source.endsWith("\n") ? source.slice(0, -1) : source).split("\n");
}

export function selectionRange(a: number, b: number): LineRange {
  return a <= b ? [a, b] : [b, a];
}

export function overlaps(
  [start, end]: LineRange,
  c: { line_start: number; line_end: number },
): boolean {
  return start <= c.line_end && c.line_start <= end;
}

export function commentsOnLine<
  T extends { file: string; line_start: number; line_end: number },
>(comments: T[], file: string, n: number): T[] {
  return comments.filter(
    (c) => c.file === file && c.line_start <= n && n <= c.line_end,
  );
}

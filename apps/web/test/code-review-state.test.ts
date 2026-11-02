import { expect, test } from "vitest";
import {
  addComment,
  canSubmit,
  commentError,
  MAX_COMMENTS,
  MAX_COMMENT_CHARS,
  MAX_SUMMARY_CHARS,
  nextSelection,
  removeComment,
  stripIds,
  updateComment,
  withId,
} from "@/lib/code-review-state";

const c = (text: string, start = 1, end = 1, file = "a.py") => ({
  file,
  line_start: start,
  line_end: end,
  text,
});

test("add, update and remove leave the old list untouched", () => {
  const one = [c("x")];
  const two = addComment(one, c("y"));
  expect(one).toHaveLength(1);
  expect(two.map((k) => k.text)).toEqual(["x", "y"]);
  const edited = updateComment(two, 0, "z");
  expect(edited[0].text).toBe("z");
  expect(two[0].text).toBe("x");
  expect(removeComment(two, 0).map((k) => k.text)).toEqual(["y"]);
});

test("commentError checks text and range against the file", () => {
  const lines = { "a.py": 10 };
  expect(commentError(c("ok", 3, 10), lines, 0)).toBeNull();
  expect(commentError(c("  ", 3, 4), lines, 0)).toMatch(/Напишите/);
  expect(commentError(c("x".repeat(MAX_COMMENT_CHARS + 1)), lines, 0)).toMatch(
    /2000/,
  );
  expect(commentError(c("ok", 3, 11), lines, 0)).toMatch(/Строки/);
  expect(commentError(c("ok", 5, 4), lines, 0)).toMatch(/Строки/);
  expect(commentError(c("ok", 0, 1), lines, 0)).toMatch(/Строки/);
  expect(commentError(c("ok", 1, 1, "b.py"), lines, 0)).toMatch(/Файл/);
  expect(commentError(c("ok"), lines, MAX_COMMENTS)).toMatch(/50/);
});

test("commentError on edit does not count the comment itself", () => {
  expect(commentError(c("ok"), { "a.py": 3 }, MAX_COMMENTS - 1)).toBeNull();
});

test("canSubmit needs a verdict and a comment or a summary", () => {
  const base = { comments: [], verdict: null, summary: "" };
  expect(canSubmit(base)).toBe(false);
  expect(canSubmit({ ...base, verdict: "approve" })).toBe(false);
  expect(canSubmit({ ...base, verdict: "approve", summary: "  " })).toBe(false);
  expect(canSubmit({ ...base, verdict: "approve", summary: "fine" })).toBe(
    true,
  );
  expect(
    canSubmit({ ...base, verdict: "request_changes", comments: [c("x")] }),
  ).toBe(true);
  expect(canSubmit({ ...base, comments: [c("x")] })).toBe(false);
  expect(
    canSubmit({
      ...base,
      verdict: "approve",
      summary: "x".repeat(MAX_SUMMARY_CHARS + 1),
    }),
  ).toBe(false);
});

test("a click starts a selection, shift extends it from the anchor", () => {
  const first = nextSelection(null, "a.py", 5, false);
  expect(first).toEqual({ file: "a.py", anchor: 5, range: [5, 5] });
  const ext = nextSelection(first, "a.py", 2, true);
  expect(ext).toEqual({ file: "a.py", anchor: 5, range: [2, 5] });
  expect(nextSelection(ext, "a.py", 8, true).range).toEqual([5, 8]);
  expect(nextSelection(ext, "a.py", 9, false).range).toEqual([9, 9]);
});

test("shift-click without a selection in that file starts a new one", () => {
  expect(nextSelection(null, "a.py", 3, true).range).toEqual([3, 3]);
  const other = { file: "b.py", anchor: 1, range: [1, 1] as [number, number] };
  expect(nextSelection(other, "a.py", 3, true)).toEqual({
    file: "a.py",
    anchor: 3,
    range: [3, 3],
  });
});

test("withId gives every comment its own id, kept by update and remove, dropped by stripIds", () => {
  const [a, b] = [withId(c("x")), withId(c("y"))];
  expect(a.id).not.toBe(b.id);
  const list = [a, b];
  expect(updateComment(list, 1, "z")[1]).toEqual({ ...b, text: "z" });
  // deleting the first comment leaves the second one's id: an open editor stays with its comment
  expect(removeComment(list, 0)[0].id).toBe(b.id);
  expect(stripIds(list)).toEqual([c("x"), c("y")]);
});

import { expect, test } from "vitest";
import {
  commentsOnLine,
  overlaps,
  selectionRange,
  splitSourceLines,
} from "@/lib/code-review-lines";

test("selectionRange orders its ends", () => {
  expect(selectionRange(7, 3)).toEqual([3, 7]);
  expect(selectionRange(3, 7)).toEqual([3, 7]);
  expect(selectionRange(4, 4)).toEqual([4, 4]);
});

test("overlaps is inclusive at both ends", () => {
  const c = { line_start: 5, line_end: 9 };
  expect(overlaps([3, 5], c)).toBe(true);
  expect(overlaps([9, 12], c)).toBe(true);
  expect(overlaps([3, 4], c)).toBe(false);
  expect(overlaps([10, 11], c)).toBe(false);
});

test("commentsOnLine filters by file and range", () => {
  const a = { file: "a.py", line_start: 2, line_end: 4 };
  const b = { file: "b.py", line_start: 2, line_end: 4 };
  expect(commentsOnLine([a, b], "a.py", 3)).toEqual([a]);
  expect(commentsOnLine([a, b], "a.py", 5)).toEqual([]);
});

// Same numbering as file_lines in apps/api/app/modules/code_review/judge.py.
test("splitSourceLines drops one trailing newline only", () => {
  expect(splitSourceLines("a\nb\n")).toEqual(["a", "b"]);
  expect(splitSourceLines("a\nb")).toEqual(["a", "b"]);
  expect(splitSourceLines("a\n\n")).toEqual(["a", ""]);
});

test("splitSourceLines splits on \\n alone", () => {
  expect(splitSourceLines("a\x0cb\rc d\ne")).toEqual(["a\x0cb\rc d", "e"]);
});

test("an empty file is one line", () => {
  expect(splitSourceLines("")).toEqual([""]);
  expect(splitSourceLines("\n")).toEqual([""]);
});

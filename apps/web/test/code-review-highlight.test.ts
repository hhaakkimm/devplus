import { expect, test } from "vitest";
import { highlightFile } from "@/lib/code-review";

test("highlightFile numbers lines like the backend and keeps the text", async () => {
  const f = await highlightFile("a.py", "x = 1\n\x0cdef f(): pass\n");
  expect(f.path).toBe("a.py");
  expect(f.lines.map((l) => l.n)).toEqual([1, 2]);
  expect(f.lines.map((l) => l.tokens.map((t) => t.text).join(""))).toEqual([
    "x = 1",
    "\x0cdef f(): pass",
  ]);
  expect(f.lines[1].tokens.some((t) => t.color)).toBe(true);
});

import path from "node:path";
import { expect, test } from "vitest";
import { loadLesson } from "@/lib/content";
import { loadTaskStatement } from "@/lib/tasks";

const FIX = path.join(__dirname, "fixtures/content");

test("loadTaskStatement returns the body without frontmatter", async () => {
  const statement = await loadTaskStatement("start", "demo", FIX);
  expect(statement).toContain("Напиши промпт.");
  expect(statement).not.toContain("title:");
});

test("loadTaskStatement is null for an unknown task, module or a module without tasks", async () => {
  expect(await loadTaskStatement("start", "nope", FIX)).toBeNull();
  expect(await loadTaskStatement("nope", "demo", FIX)).toBeNull();
  expect(await loadTaskStatement("internet", "demo", FIX)).toBeNull();
});

test("a task is not a lesson", async () => {
  expect(await loadLesson("start", "demo", FIX)).toBeNull();
});

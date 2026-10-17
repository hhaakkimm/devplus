import path from "node:path";
import { expect, test } from "vitest";
import { loadCurriculum, loadLesson } from "@/lib/content";
import { moduleProgress } from "@/lib/progress";

const FIX = path.join(__dirname, "fixtures/content");

test("orders modules and lessons by prefix and strips it", async () => {
  const mods = await loadCurriculum(FIX);
  expect(mods.map((m) => m.slug)).toEqual(["start", "internet"]);
  expect(mods[1].lessons.map((l) => [l.slug, l.title])).toEqual([
    ["internet/dns", "DNS"],
    ["internet/tcp", "TCP"],
  ]);
});

test("ignores files that are not lessons", async () => {
  const mods = await loadCurriculum(FIX);
  expect(mods[1].lessons).toHaveLength(2);
});

test("names the file when frontmatter is incomplete", async () => {
  await expect(
    loadCurriculum(path.join(__dirname, "fixtures/broken")),
  ).rejects.toThrow(/01-no-title\.mdx: frontmatter needs title and summary/);
});

test("names the module dir when _module.json is missing", async () => {
  await expect(
    loadCurriculum(path.join(__dirname, "fixtures/no-module")),
  ).rejects.toThrow(/00-y: missing _module\.json/);
});

test("loadLesson returns body without frontmatter, null when missing", async () => {
  const lesson = await loadLesson("internet", "dns", FIX);
  expect(lesson?.source).not.toContain("title:");
  expect(await loadLesson("internet", "nope", FIX)).toBeNull();
});

test("moduleProgress ignores marks for lessons that no longer exist", async () => {
  const [, internet] = await loadCurriculum(FIX);
  expect(
    moduleProgress(internet, new Set(["internet/dns", "gone/old"])),
  ).toEqual({ done: 1, total: 2 });
});

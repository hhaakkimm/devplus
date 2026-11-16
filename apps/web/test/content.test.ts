import path from "node:path";
import { expect, test } from "vitest";
import {
  groupLessons,
  loadCurriculum,
  loadLesson,
  type LessonMeta,
} from "@/lib/content";
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

test("names the file when frontmatter is not valid YAML", async () => {
  await expect(
    loadCurriculum(path.join(__dirname, "fixtures/bad-yaml")),
  ).rejects.toThrow(/01-bad-yaml\.mdx: /);
});

test("names _module.json when it is not valid JSON", async () => {
  await expect(
    loadCurriculum(path.join(__dirname, "fixtures/bad-json")),
  ).rejects.toThrow(/00-j.*_module\.json: /);
});

test("names the module dir when _module.json lacks a title", async () => {
  await expect(
    loadCurriculum(path.join(__dirname, "fixtures/bad-module")),
  ).rejects.toThrow(/00-t: _module\.json needs title and description/);
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

test("reads sections and the lesson order from the file prefix", async () => {
  const [start, internet] = await loadCurriculum(FIX);
  expect(internet.sections).toEqual([
    { title: "Адресация", from: 1 },
    { title: "Транспорт", from: 2 },
  ]);
  expect(internet.lessons.map((l) => l.order)).toEqual([1, 2]);
  expect(start.sections).toEqual([]);
});

test("names the module dir when sections are malformed or unsorted", async () => {
  await expect(
    loadCurriculum(path.join(__dirname, "fixtures/bad-sections")),
  ).rejects.toThrow(/00-s: _module\.json sections need a title and a number/);
  await expect(
    loadCurriculum(path.join(__dirname, "fixtures/unsorted-sections")),
  ).rejects.toThrow(/00-u: _module\.json sections must go in ascending "from"/);
});

const lesson = (order: number): LessonMeta => ({
  slug: `m/l${order}`,
  moduleSlug: "m",
  lessonSlug: `l${order}`,
  title: `L${order}`,
  summary: "",
  order,
});
const titles = (g: ReturnType<typeof groupLessons>) =>
  g.map((x) => [x.title, x.lessons.map((l) => l.order)]);

test("groupLessons: no sections is one untitled group", () => {
  const lessons = [lesson(1), lesson(2)];
  expect(titles(groupLessons({ lessons, sections: [] }))).toEqual([
    [null, [1, 2]],
  ]);
});

test("groupLessons: lessons before the first section stay untitled, empty sections are dropped", () => {
  const lessons = [lesson(1), lesson(2), lesson(5), lesson(6)];
  const sections = [
    { title: "Основы", from: 5 },
    { title: "Пусто", from: 7 },
  ];
  expect(titles(groupLessons({ lessons, sections }))).toEqual([
    [null, [1, 2]],
    ["Основы", [5, 6]],
  ]);
});

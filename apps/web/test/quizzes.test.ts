import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterAll, beforeAll, expect, test } from "vitest";
import { CONTENT_DIR, loadCurriculum } from "@/lib/content";
import { loadQuiz, loadQuizCatalog, parseQuiz } from "@/lib/quizzes";

const tf = { type: "true_false", level: "junior", question: "q", answer: true };
const choice = {
  type: "choice",
  level: "mid",
  question: "q",
  options: ["a", "b", "c", "d"],
  answer: 3,
};
const withExplanation = (q: object) => ({ ...q, explanation: "e" });
const quiz = (title: string, ...questions: object[]) => ({
  title,
  source: "https://example.com/x",
  questions: questions.map(withExplanation),
});

let dir: string;
beforeAll(async () => {
  dir = await fs.mkdtemp(path.join(os.tmpdir(), "quizzes-"));
  const put = async (rel: string, data: unknown) => {
    await fs.mkdir(path.dirname(path.join(dir, rel)), { recursive: true });
    await fs.writeFile(path.join(dir, rel), JSON.stringify(data));
  };
  await put("20-core/_module.json", { title: "Core", description: "d" });
  await put("20-core/quizzes/b-second.json", quiz("Second", tf));
  await put("20-core/quizzes/a-first.json", quiz("First", tf, choice));
  await put("20-core/quizzes/notes.txt", "ignored");
  await put("21-empty/_module.json", { title: "Empty", description: "d" });
});
afterAll(() => fs.rm(dir, { recursive: true }));

test("catalog groups quizzes by module, sorted by name, skipping modules without quizzes", async () => {
  const catalog = await loadQuizCatalog(dir);
  expect(catalog).toHaveLength(1);
  expect(catalog[0]).toMatchObject({ slug: "core", title: "Core" });
  expect(catalog[0].quizzes.map((q) => [q.slug, q.title, q.count])).toEqual([
    ["core/a-first", "First", 2],
    ["core/b-second", "Second", 1],
  ]);
});

test("loadQuiz returns the full quiz and null for unknown slugs", async () => {
  const q = await loadQuiz("core", "a-first", dir);
  expect(q?.questions).toHaveLength(2);
  expect(q?.source).toBe("https://example.com/x");
  expect(await loadQuiz("core", "nope", dir)).toBeNull();
  expect(await loadQuiz("nope", "a-first", dir)).toBeNull();
});

test("URL slugs are matched against listed names, never joined into a path", async () => {
  expect(await loadQuiz("core", "../_module", dir)).toBeNull();
  expect(await loadQuiz("../core", "a-first", dir)).toBeNull();
});

const bad: [string, object][] = [
  ["empty title", { ...quiz("", tf) }],
  ["no questions", { title: "t", questions: [] }],
  ["unknown type", quiz("t", { ...tf, type: "essay" })],
  ["unknown level", quiz("t", { ...tf, level: "god" })],
  ["empty question text", quiz("t", { ...tf, question: " " })],
  ["missing explanation", { title: "t", questions: [tf] }],
  ["non-boolean true_false answer", quiz("t", { ...tf, answer: "yes" })],
  ["choice with 3 options", quiz("t", { ...choice, options: ["a", "b", "c"] })],
  ["choice answer out of range", quiz("t", { ...choice, answer: 4 })],
  [
    "ranking answer not a permutation",
    quiz("t", {
      type: "ranking",
      level: "mid",
      question: "q",
      items: ["a", "b", "c"],
      answer: [0, 0, 1],
    }),
  ],
  [
    "matching sides of different length",
    quiz("t", {
      type: "matching",
      level: "mid",
      question: "q",
      left: ["a", "b"],
      right: ["x"],
      answer: [0, 1],
    }),
  ],
  [
    "matching answer not a permutation",
    quiz("t", {
      type: "matching",
      level: "mid",
      question: "q",
      left: ["a", "b"],
      right: ["x", "y"],
      answer: [1, 1],
    }),
  ],
];
test.each(bad)("rejects %s and names the file", (_, raw) => {
  expect(() => parseQuiz("m/q.json", "m", "q", raw)).toThrow(/^m\/q\.json: /);
});

test("accepts a valid ranking and matching", () => {
  const ok = quiz(
    "t",
    {
      type: "ranking",
      level: "senior",
      question: "q",
      items: ["a", "b", "c"],
      answer: [2, 0, 1],
    },
    {
      type: "matching",
      level: "staff",
      question: "q",
      left: ["a", "b"],
      right: ["x", "y"],
      answer: [1, 0],
    },
  );
  expect(parseQuiz("f", "m", "q", ok).questions).toHaveLength(2);
});

test("every real quiz passes the loader", async () => {
  const catalog = await loadQuizCatalog(CONTENT_DIR);
  expect(catalog.flatMap((m) => m.quizzes).length).toBeGreaterThan(0);
  for (const m of catalog) {
    for (const q of m.quizzes) expect(q.count, q.slug).toBeGreaterThan(0);
  }
});

test("every lesson's quiz: points at an existing quiz", async () => {
  const lessons = (await loadCurriculum()).flatMap((m) => m.lessons);
  for (const l of lessons.filter((l) => l.quiz)) {
    expect(await loadQuiz(l.moduleSlug, l.quiz!), l.slug).not.toBeNull();
  }
});

test("names the file when the JSON is broken", async () => {
  await fs.writeFile(path.join(dir, "20-core/quizzes/broken.json"), "{nope");
  await expect(loadQuizCatalog(dir)).rejects.toThrow(/broken\.json: /);
  await fs.rm(path.join(dir, "20-core/quizzes/broken.json"));
});

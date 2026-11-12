import fs from "node:fs/promises";
import path from "node:path";
import { compile } from "@mdx-js/mdx";
import matter from "gray-matter";
import remarkGfm from "remark-gfm";
import { expect, test } from "vitest";
import { CONTENT_DIR, loadCurriculum, loadLesson } from "@/lib/content";

// next build does not compile MDX (pages render dynamically), so CI does it here.
test("every real lesson compiles as MDX", async () => {
  const lessons = (await loadCurriculum()).flatMap((m) => m.lessons);
  expect(lessons.length).toBeGreaterThan(0);
  for (const { moduleSlug, lessonSlug, slug } of lessons) {
    const lesson = (await loadLesson(moduleSlug, lessonSlug))!;
    // compile errors carry only line:column, so name the lesson ourselves.
    await compile(lesson.source, { remarkPlugins: [remarkGfm] }).catch(
      (e: Error) => {
        throw new Error(`${slug}: ${e.message}`);
      },
    );
  }
});

// Task statements are MDX too (the API reads their title and summary, the web renders them).
test("every real task statement compiles as MDX", async () => {
  const files = (await fs.readdir(CONTENT_DIR, { recursive: true }))
    .filter((f) => /^[^/]+\/tasks\/[^/]+\.mdx$/.test(f))
    .sort();
  expect(files.length).toBeGreaterThan(0);
  for (const file of files) {
    const { data, content } = matter(
      await fs.readFile(path.join(CONTENT_DIR, file), "utf8"),
    );
    expect(typeof data.title, `${file}: title`).toBe("string");
    expect(typeof data.summary, `${file}: summary`).toBe("string");
    await compile(content).catch((e: Error) => {
      throw new Error(`${file}: ${e.message}`);
    });
  }
});

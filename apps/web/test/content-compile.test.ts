import { compile } from "@mdx-js/mdx";
import { expect, test } from "vitest";
import { loadCurriculum, loadLesson } from "@/lib/content";

// next build does not compile MDX (pages render dynamically), so CI does it here.
test("every real lesson compiles as MDX", async () => {
  const lessons = (await loadCurriculum()).flatMap((m) => m.lessons);
  expect(lessons.length).toBeGreaterThan(0);
  for (const { moduleSlug, lessonSlug, slug } of lessons) {
    const lesson = (await loadLesson(moduleSlug, lessonSlug))!;
    // compile errors carry only line:column, so name the lesson ourselves.
    await compile(lesson.source).catch((e: Error) => {
      throw new Error(`${slug}: ${e.message}`);
    });
  }
});

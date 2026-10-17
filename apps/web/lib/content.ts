import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";

export type LessonMeta = {
  slug: string; // "module/lesson"
  moduleSlug: string;
  lessonSlug: string;
  title: string;
  summary: string;
};
export type Module = {
  slug: string;
  title: string;
  description: string;
  lessons: LessonMeta[];
};
export type Lesson = LessonMeta & { source: string };

export const CONTENT_DIR =
  process.env.CONTENT_DIR ?? path.resolve(process.cwd(), "../../content");

const MODULE_RE = /^\d{2}-([a-z0-9-]+)$/;
const LESSON_RE = /^\d{2}-([a-z0-9-]+)\.mdx$/;

// Names matching `re`, ordered by their numeric prefix. Everything else is ignored.
async function list(dir: string, re: RegExp, dirs: boolean) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  return entries
    .filter((e) => e.isDirectory() === dirs && re.test(e.name))
    .map((e) => e.name)
    .sort();
}

const slugOf = (name: string, re: RegExp) => name.match(re)![1];

async function readLesson(
  file: string,
  moduleSlug: string,
  lessonSlug: string,
): Promise<{ meta: LessonMeta; source: string }> {
  const { data, content } = matter(await fs.readFile(file, "utf8"));
  const { title, summary } = data;
  if (typeof title !== "string" || typeof summary !== "string") {
    throw new Error(`${file}: frontmatter needs title and summary`);
  }
  const slug = `${moduleSlug}/${lessonSlug}`;
  return {
    meta: { slug, moduleSlug, lessonSlug, title, summary },
    source: content,
  };
}

export async function loadCurriculum(dir = CONTENT_DIR): Promise<Module[]> {
  return Promise.all(
    (await list(dir, MODULE_RE, true)).map(async (name) => {
      const moduleDir = path.join(dir, name);
      const slug = slugOf(name, MODULE_RE);
      let raw: string;
      try {
        raw = await fs.readFile(path.join(moduleDir, "_module.json"), "utf8");
      } catch (e) {
        if ((e as NodeJS.ErrnoException).code === "ENOENT") {
          throw new Error(`${moduleDir}: missing _module.json`);
        }
        throw e;
      }
      const { title, description } = JSON.parse(raw);
      const files = await list(moduleDir, LESSON_RE, false);
      const lessons = await Promise.all(
        // Only meta: curriculum is for listings, loadLesson returns the body.
        files.map(async (file) => {
          const lesson = await readLesson(
            path.join(moduleDir, file),
            slug,
            slugOf(file, LESSON_RE),
          );
          return lesson.meta;
        }),
      );
      return { slug, title, description, lessons };
    }),
  );
}

export async function loadLesson(
  moduleSlug: string,
  lessonSlug: string,
  dir = CONTENT_DIR,
): Promise<Lesson | null> {
  // Slugs come from the URL: match them against listed names, never join them into a path.
  const moduleName = (await list(dir, MODULE_RE, true)).find(
    (n) => slugOf(n, MODULE_RE) === moduleSlug,
  );
  if (!moduleName) return null;
  const moduleDir = path.join(dir, moduleName);
  const file = (await list(moduleDir, LESSON_RE, false)).find(
    (n) => slugOf(n, LESSON_RE) === lessonSlug,
  );
  if (!file) return null;
  const { meta, source } = await readLesson(
    path.join(moduleDir, file),
    moduleSlug,
    lessonSlug,
  );
  return { ...meta, source };
}

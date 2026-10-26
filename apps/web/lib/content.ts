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

// turbopackIgnore: otherwise the tracer pulls the whole project into the standalone output.
export const CONTENT_DIR =
  process.env.CONTENT_DIR ??
  path.resolve(/*turbopackIgnore: true*/ process.cwd(), "../../content");

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

// Parser errors carry only a position, so name the file ourselves.
function parse<T>(file: string, fn: () => T): T {
  try {
    return fn();
  } catch (e) {
    throw new Error(`${file}: ${(e as Error).message}`);
  }
}

async function readLesson(
  file: string,
  moduleSlug: string,
  lessonSlug: string,
): Promise<{ meta: LessonMeta; source: string }> {
  const raw = await fs.readFile(file, "utf8");
  const { data, content } = parse(file, () => matter(raw));
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
      const moduleFile = path.join(moduleDir, "_module.json");
      let raw: string;
      try {
        raw = await fs.readFile(moduleFile, "utf8");
      } catch (e) {
        if ((e as NodeJS.ErrnoException).code === "ENOENT") {
          throw new Error(`${moduleDir}: missing _module.json`);
        }
        throw e;
      }
      const { title, description } = parse(
        moduleFile,
        () => JSON.parse(raw) ?? {},
      );
      if (typeof title !== "string" || typeof description !== "string") {
        throw new Error(
          `${moduleDir}: _module.json needs title and description`,
        );
      }
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

// `folder` is a subfolder of the module that holds the MDX files ("tasks" for Trainer tasks).
export async function loadLesson(
  moduleSlug: string,
  lessonSlug: string,
  dir = CONTENT_DIR,
  folder = "",
): Promise<Lesson | null> {
  // Slugs come from the URL: match them against listed names, never join them into a path.
  const moduleName = (await list(dir, MODULE_RE, true)).find(
    (n) => slugOf(n, MODULE_RE) === moduleSlug,
  );
  if (!moduleName) return null;
  const lessonDir = path.join(dir, moduleName, folder);
  const files = await list(lessonDir, LESSON_RE, false).catch((e) => {
    if (e.code === "ENOENT") return []; // a module without that folder
    throw e;
  });
  const file = files.find((n) => slugOf(n, LESSON_RE) === lessonSlug);
  if (!file) return null;
  const { meta, source } = await readLesson(
    path.join(lessonDir, file),
    moduleSlug,
    lessonSlug,
  );
  return { ...meta, source };
}

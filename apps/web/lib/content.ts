import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";

export type LessonMeta = {
  slug: string; // "module/lesson"
  moduleSlug: string;
  lessonSlug: string;
  title: string;
  summary: string;
  order: number; // the numeric prefix of the file: "05-x.mdx" is 5
  quiz?: string; // slug of a quiz from the same module's quizzes/ folder
};
// A subsection of a module: starts at the lesson whose `order` is `from`, runs to the next section.
export type Section = { title: string; from: number };
export type Module = {
  slug: string;
  title: string;
  description: string;
  sections: Section[]; // [] for a flat module
  lessons: LessonMeta[];
};
// `title` is null for lessons that come before the first section (or in a flat module).
export type LessonGroup = { title: string | null; lessons: LessonMeta[] };
// `en`: the English original from the sibling NN-slug.en.mdx (frontmatter holds only its title).
export type Lesson = LessonMeta & {
  source: string;
  en?: { title: string; source: string };
};

// turbopackIgnore: otherwise the tracer pulls the whole project into the standalone output.
export const CONTENT_DIR =
  process.env.CONTENT_DIR ??
  path.resolve(/*turbopackIgnore: true*/ process.cwd(), "../../content");

export const MODULE_RE = /^\d{2}-([a-z0-9-]+)$/;
const LESSON_RE = /^\d{2}-([a-z0-9-]+)\.mdx$/;

// Names matching `re`, ordered by their numeric prefix. Everything else is ignored.
export async function list(dir: string, re: RegExp, dirs: boolean) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  return entries
    .filter((e) => e.isDirectory() === dirs && re.test(e.name))
    .map((e) => e.name)
    .sort();
}

export const slugOf = (name: string, re: RegExp) => name.match(re)![1];

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
  const { title, summary, quiz } = data;
  if (typeof title !== "string" || typeof summary !== "string") {
    throw new Error(`${file}: frontmatter needs title and summary`);
  }
  const slug = `${moduleSlug}/${lessonSlug}`;
  return {
    meta: {
      slug,
      moduleSlug,
      lessonSlug,
      title,
      summary,
      order: Number(path.basename(file).slice(0, 2)),
      ...(typeof quiz === "string" ? { quiz } : {}),
    },
    source: content,
  };
}

function parseSections(moduleDir: string, raw: unknown): Section[] {
  if (raw === undefined) return [];
  const fail = (rest: string) =>
    new Error(`${moduleDir}: _module.json sections ${rest}`);
  if (!Array.isArray(raw)) throw fail('need a title and a number "from"');
  const sections = raw.map((s) => {
    if (typeof s?.title !== "string" || !Number.isInteger(s?.from)) {
      throw fail('need a title and a number "from"');
    }
    return { title: s.title, from: s.from as number };
  });
  sections.forEach((s, i) => {
    if (i > 0 && s.from <= sections[i - 1].from) {
      throw fail('must go in ascending "from"');
    }
  });
  return sections;
}

// Lessons sit in the first section whose `from` they reach; sections without lessons are dropped.
export function groupLessons(
  m: Pick<Module, "lessons" | "sections">,
): LessonGroup[] {
  const groups: LessonGroup[] = [{ title: null, lessons: [] }];
  for (const s of m.sections) groups.push({ title: s.title, lessons: [] });
  for (const l of m.lessons) {
    const at = m.sections.filter((s) => s.from <= l.order).length;
    groups[at].lessons.push(l);
  }
  return groups.filter((g) => g.lessons.length > 0);
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
      const {
        title,
        description,
        sections: rawSections,
      } = parse(moduleFile, () => JSON.parse(raw) ?? {});
      if (typeof title !== "string" || typeof description !== "string") {
        throw new Error(
          `${moduleDir}: _module.json needs title and description`,
        );
      }
      const sections = parseSections(moduleDir, rawSections);
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
      return { slug, title, description, sections, lessons };
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
  const full = path.join(lessonDir, file);
  const { meta, source } = await readLesson(full, moduleSlug, lessonSlug);
  const enFile = full.replace(/\.mdx$/, ".en.mdx");
  const raw = await fs.readFile(enFile, "utf8").catch((e) => {
    if (e.code === "ENOENT") return null; // not every lesson has an English version
    throw e;
  });
  if (raw === null) return { ...meta, source };
  const { data, content } = parse(enFile, () => matter(raw));
  if (typeof data.title !== "string") {
    throw new Error(`${enFile}: frontmatter needs title`);
  }
  return { ...meta, source, en: { title: data.title, source: content } };
}

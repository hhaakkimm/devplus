import { CONTENT_DIR, loadLesson } from "@/lib/content";

// The statement of a Trainer task, `<NN-module>/tasks/<NN-task>.mdx`, without its frontmatter.
// The title and the rest come from the API, which also reads the YAML beside it.
export async function loadTaskStatement(
  moduleSlug: string,
  taskSlug: string,
  dir = CONTENT_DIR,
): Promise<string | null> {
  return (await loadLesson(moduleSlug, taskSlug, dir, "tasks"))?.source ?? null;
}

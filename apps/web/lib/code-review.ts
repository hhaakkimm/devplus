import { codeToTokens, createCssVariablesTheme } from "shiki";
import { serverApi } from "@/lib/api";
import { unwrap } from "@/lib/evals";
import { splitSourceLines } from "@/lib/code-review-lines";

export async function loadReviewTasks() {
  const res = await (await serverApi()).GET("/api/code-review/tasks");
  return unwrap(res, "GET /api/code-review/tasks");
}

export async function loadReviewTask(moduleSlug: string, slug: string) {
  const res = await (
    await serverApi()
  ).GET("/api/code-review/tasks/{module}/{slug}", {
    params: { path: { module: moduleSlug, slug } },
  });
  return unwrap(res, "GET /api/code-review/tasks/{module}/{slug}");
}

// The user's attempts, newest first.
export async function loadReviewAttempts() {
  const res = await (await serverApi()).GET("/api/code-review/attempts");
  return unwrap(res, "GET /api/code-review/attempts");
}

export async function loadReviewAttempt(id: string) {
  const res = await (
    await serverApi()
  ).GET("/api/code-review/attempts/{attempt_id}", {
    params: { path: { attempt_id: id } },
  });
  return unwrap(res, "GET /api/code-review/attempts/{id}");
}

// Starts an attempt and returns its draft. For server components only: a browser calls the API itself.
export async function createReviewAttempt(moduleSlug: string, slug: string) {
  const res = await (
    await serverApi()
  ).POST("/api/code-review/tasks/{module}/{slug}/attempts", {
    params: { path: { module: moduleSlug, slug } },
  });
  return unwrap(res, "POST /api/code-review/tasks/{module}/{slug}/attempts");
}

export type HighlightedFile = {
  path: string;
  lines: { n: number; tokens: { text: string; color?: string }[] }[];
};

// Token colors are CSS variables (--shiki-token-*), set for light and dark in globals.css,
// so the page follows the `.dark` class without re-highlighting.
const theme = createCssVariablesTheme({
  name: "css-variables",
  variablePrefix: "--shiki-",
  variableDefaults: {},
  fontStyle: false,
});

export async function highlightFile(
  path: string,
  source: string,
): Promise<HighlightedFile> {
  const text = splitSourceLines(source);
  const { tokens } = await codeToTokens(text.join("\n"), {
    lang: "python",
    theme,
  });
  // shiki also breaks lines on \r; if its count differs from ours, show plain text rather than shift numbers.
  const aligned = tokens.length === text.length;
  return {
    path,
    lines: text.map((line, i) => ({
      n: i + 1,
      tokens: aligned
        ? tokens[i].map((t) => ({ text: t.content, color: t.color }))
        : [{ text: line }],
    })),
  };
}

import { notFound } from "next/navigation";
import { serverApi } from "@/lib/api";
import { redirectOnAuthError } from "@/lib/session";

// A missing or foreign id answers 404 and a malformed one 422: both are "not found" for a page.
function unwrap<T>(
  { data, response }: { data?: T; response: Response },
  what: string,
): T {
  redirectOnAuthError(response.status);
  if (response.status === 404 || response.status === 422) notFound();
  if (data === undefined) throw new Error(`${what} failed: ${response.status}`);
  return data;
}

export async function loadPrompts() {
  const res = await (await serverApi()).GET("/api/evals/prompts");
  return unwrap(res, "GET /api/evals/prompts");
}

export async function loadPrompt(id: string) {
  const res = await (
    await serverApi()
  ).GET("/api/evals/prompts/{prompt_id}", {
    params: { path: { prompt_id: id } },
  });
  return unwrap(res, "GET /api/evals/prompts/{id}");
}

export async function loadDatasets() {
  const res = await (await serverApi()).GET("/api/evals/datasets");
  return unwrap(res, "GET /api/evals/datasets");
}

export async function loadDataset(id: string) {
  const res = await (
    await serverApi()
  ).GET("/api/evals/datasets/{dataset_id}", {
    params: { path: { dataset_id: id } },
  });
  return unwrap(res, "GET /api/evals/datasets/{id}");
}

export async function loadRun(id: string) {
  const res = await (
    await serverApi()
  ).GET("/api/evals/runs/{run_id}", { params: { path: { run_id: id } } });
  return unwrap(res, "GET /api/evals/runs/{id}");
}

export async function loadRuns(promptId: string) {
  const res = await (
    await serverApi()
  ).GET("/api/evals/runs", { params: { query: { prompt_id: promptId } } });
  return unwrap(res, "GET /api/evals/runs");
}

// The text of a version, or null when its prompt is gone or no longer visible to the user.
export async function loadVersion(promptId: string, versionId: string) {
  const res = await (
    await serverApi()
  ).GET("/api/evals/prompts/{prompt_id}", {
    params: { path: { prompt_id: promptId } },
  });
  if (res.response.status === 404) return null;
  return (
    unwrap(res, "GET /api/evals/prompts/{id}").versions.find(
      (v) => v.id === versionId,
    ) ?? null
  );
}

export async function loadReview(id: string) {
  const res = await (
    await serverApi()
  ).GET("/api/review/{review_id}", { params: { path: { review_id: id } } });
  return unwrap(res, "GET /api/review/{id}");
}

export async function loadTasks() {
  const res = await (await serverApi()).GET("/api/trainer/tasks");
  return unwrap(res, "GET /api/trainer/tasks");
}

// The user's attempts at a task, newest first, without per-case results.
export async function loadAttempts(moduleSlug: string, taskSlug: string) {
  const res = await (
    await serverApi()
  ).GET("/api/trainer/tasks/{module}/{task}/attempts", {
    params: { path: { module: moduleSlug, task: taskSlug } },
  });
  return unwrap(res, "GET /api/trainer/tasks/{module}/{task}/attempts");
}

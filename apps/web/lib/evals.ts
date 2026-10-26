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

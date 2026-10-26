import type { components } from "@devplus/api-client";
import { redirect } from "next/navigation";
import { serverApi } from "@/lib/api";
import { SIGN_IN_URL } from "@/lib/browser-api";

// Layout and page render in parallel, so both must map auth errors to the same redirect.
export function redirectOnAuthError(status: number) {
  if (status === 401) redirect(SIGN_IN_URL);
  if (status === 403) redirect("/no-access");
}

export async function requireUser(): Promise<components["schemas"]["MeOut"]> {
  const { data, response } = await (await serverApi()).GET("/api/me");
  redirectOnAuthError(response.status);
  if (!data) throw new Error(`GET /api/me failed: ${response.status}`);
  return data;
}

export async function loadDone(): Promise<Set<string>> {
  const { data, response } = await (await serverApi()).GET("/api/progress");
  redirectOnAuthError(response.status);
  if (!data) throw new Error(`GET /api/progress failed: ${response.status}`);
  return new Set(data.completed.map((c) => c.lesson_slug));
}

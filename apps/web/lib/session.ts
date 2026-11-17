import type { components } from "@devplus/api-client";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { serverApi } from "@/lib/api";
import { signInUrl } from "@/lib/miniapp";

// Layout and page render in parallel, so both must map auth errors to the same redirect.
export async function redirectOnAuthError(status: number) {
  if (status === 401) redirect(signInUrl((await cookies()).toString()));
  if (status === 403) redirect("/no-access");
}

export async function requireUser(): Promise<components["schemas"]["MeOut"]> {
  const { data, response } = await (await serverApi()).GET("/api/me");
  await redirectOnAuthError(response.status);
  if (!data) throw new Error(`GET /api/me failed: ${response.status}`);
  return data;
}

export type QuizResult = { best_score: number; total: number };

// Best result per quiz slug ("module/quiz").
export async function loadQuizResults(): Promise<Map<string, QuizResult>> {
  const { data, response } = await (
    await serverApi()
  ).GET("/api/quizzes/results");
  await redirectOnAuthError(response.status);
  if (!data) {
    throw new Error(`GET /api/quizzes/results failed: ${response.status}`);
  }
  return new Map(data.results.map((r) => [r.quiz_slug, r]));
}

// The three latest attempts at one quiz, newest first.
export async function loadQuizAttempts(module: string, quiz: string) {
  const { data, response } = await (
    await serverApi()
  ).GET("/api/quizzes/{module}/{quiz}/attempts", {
    params: { path: { module, quiz } },
  });
  await redirectOnAuthError(response.status);
  // A malformed slug in the URL is a 404 page (the quiz is not found), not a crash here.
  if (response.status === 422) return [];
  if (!data) {
    throw new Error(`GET quiz attempts failed: ${response.status}`);
  }
  return data.attempts;
}

export async function loadDone(): Promise<Set<string>> {
  const { data, response } = await (await serverApi()).GET("/api/progress");
  await redirectOnAuthError(response.status);
  if (!data) throw new Error(`GET /api/progress failed: ${response.status}`);
  return new Set(data.completed.map((c) => c.lesson_slug));
}

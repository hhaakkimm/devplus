import { createApiClient } from "@devplus/api-client";

export const browserApi = createApiClient("");

// FastAPI answers {"detail": "..."}; request validation errors carry a list of {msg} instead.
export function apiDetail(error: unknown, status: number): string {
  const detail = (error as { detail?: unknown } | undefined)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail.map((d) =>
      String(d?.msg ?? "").replace(/^Value error, /, ""),
    );
    if (msgs.some(Boolean)) return msgs.filter(Boolean).join("; ");
  }
  return `Ошибка ${status}`;
}

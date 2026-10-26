import type { components } from "@devplus/api-client";

type Result = components["schemas"]["ResultOut"];

export const isActive = (status: string) =>
  status === "queued" || status === "running";

export function statusText(run: {
  status: string;
  cases_done: number;
  cases_total: number;
}): string {
  switch (run.status) {
    case "queued":
      return "В очереди";
    case "running":
      return `Выполняется ${run.cases_done} из ${run.cases_total}`;
    case "done":
      return "Готово";
    case "failed":
      return "Ошибка";
    case "over_budget":
      return "Остановлен: превышен лимит";
    default:
      return run.status;
  }
}

// The API sends money as decimal strings; a float is precise enough to show them.
export const money = (value: string, digits = 4) =>
  `$${Number(value).toFixed(digits)}`;

export const scoreText = (score: number | null | undefined) =>
  score == null ? "—" : score.toFixed(2);

// B minus A, rounded first so that a tiny negative never reads "-0.00".
export function deltaText(a?: number, b?: number): string {
  if (a === undefined || b === undefined) return "—";
  const d = Math.round((b - a) * 100) / 100;
  return d > 0 ? `+${d.toFixed(2)}` : d.toFixed(2);
}

export function alignByPosition(a: Result[], b: Result[]) {
  const positions = [...new Set([...a, ...b].map((r) => r.position))].sort(
    (x, y) => x - y,
  );
  return positions.map((position) => ({
    position,
    a: a.find((r) => r.position === position),
    b: b.find((r) => r.position === position),
  }));
}

// shortcut: time in UTC, the server does not know the user's zone; change with a client-side clock
export const dateText = (iso: string) =>
  new Date(iso).toLocaleString("ru-RU", {
    timeZone: "UTC",
    dateStyle: "short",
    timeStyle: "short",
  }) + " UTC";

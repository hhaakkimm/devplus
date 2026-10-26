import type { components } from "@devplus/api-client";

type CaseIn = components["schemas"]["CaseIn"];

const MAX_CASES = 1000;

const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

// The same rules as CaseIn in apps/api/app/modules/evals/schemas.py (the API stays the judge:
// it also checks size and NUL). Returns the case or a problem text.
export function checkCase(v: unknown): CaseIn | string {
  if (!isObject(v)) return "ожидается JSON-объект";
  const extra = Object.keys(v).filter(
    (k) => k !== "variables" && k !== "expected",
  );
  if (extra.length) return `лишние поля: ${extra.join(", ")}`;
  const { variables, expected = null } = v;
  if (!isObject(variables)) return "variables: ожидается объект";
  const bad = Object.keys(variables).filter(
    (k) => typeof variables[k] !== "string",
  );
  if (bad.length)
    return `variables: значение должно быть строкой (${bad.join(", ")})`;
  if (expected !== null && typeof expected !== "string") {
    return "expected: ожидается строка или null";
  }
  return { variables: variables as Record<string, string>, expected };
}

// Mirrors _parse_jsonl in apps/api/app/modules/evals/service.py: BOM, CRLF and blank lines are
// fine, and "Строка N" is the 1-based physical line, blank ones included.
export function parseJsonl(text: string): {
  cases: CaseIn[];
  errors: string[];
} {
  const lines = text
    .replace(/^﻿/, "")
    .split("\n")
    .map((line, i) => [i + 1, line.trim()] as const)
    .filter(([, line]) => line);
  if (lines.length > MAX_CASES) {
    return { cases: [], errors: [`В датасете не больше ${MAX_CASES} кейсов`] };
  }
  const cases: CaseIn[] = [];
  const errors: string[] = [];
  for (const [n, line] of lines) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(line);
    } catch {
      errors.push(`Строка ${n}: некорректный JSON`);
      continue;
    }
    const checked = checkCase(parsed);
    if (typeof checked === "string") errors.push(`Строка ${n}: ${checked}`);
    else cases.push(checked);
  }
  return { cases, errors };
}

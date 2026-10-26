import type { components } from "@devplus/api-client";

type RunIn = components["schemas"]["RunIn"];
export type Grader = RunIn["graders"][number];
type Rubric = components["schemas"]["RubricSection"][];

export const GRADER_TYPES = [
  "exact",
  "regex",
  "json_schema",
  "llm_judge",
] as const;
export type GraderType = (typeof GRADER_TYPES)[number];
export type GraderRow = { key: number; type: GraderType };

export const MAX_GRADERS = 5;

// One rubric section per line: «Название | Описание | вес», the weight is optional (1).
export function parseRubric(
  text: string,
): { rubric: Rubric } | { error: string } {
  const rubric: Rubric = [];
  const lines = text.split("\n");
  for (const [i, line] of lines.entries()) {
    if (!line.trim()) continue;
    const parts = line.split("|").map((p) => p.trim());
    const [name, description, weight] = parts;
    if (parts.length < 2 || parts.length > 3 || !name || !description) {
      return {
        error: `Рубрика, строка ${i + 1}: ожидается «Название | Описание | вес»`,
      };
    }
    const w = weight === undefined ? 1 : Number(weight);
    if (!(w > 0 && w <= 100)) {
      return {
        error: `Рубрика, строка ${i + 1}: вес — число больше 0 и не больше 100`,
      };
    }
    rubric.push({ name, description, weight: w });
  }
  if (rubric.length === 0)
    return { error: "Рубрика: нужен хотя бы один раздел" };
  return { rubric };
}

// Settings of the grader with row key K sit in the form under "K.<field>".
export function buildGraders(
  rows: GraderRow[],
  f: FormData,
): { graders: Grader[] } | { error: string } {
  if (rows.length === 0) return { error: "Добавьте хотя бы один оценщик" };
  const graders: Grader[] = [];
  for (const { key, type } of rows) {
    const get = (field: string) => String(f.get(`${key}.${field}`) ?? "");
    const on = (field: string) => f.get(`${key}.${field}`) !== null; // a checkbox
    switch (type) {
      case "exact":
        graders.push({ type, ignore_case: on("ignore_case") });
        break;
      case "regex":
        graders.push({
          type,
          pattern: get("pattern"),
          must_match: on("must_match"),
        });
        break;
      case "json_schema": {
        let schema: unknown;
        try {
          schema = JSON.parse(get("schema"));
        } catch {
          return { error: "JSON-схема оценщика: некорректный JSON" };
        }
        if (
          schema === null ||
          typeof schema !== "object" ||
          Array.isArray(schema)
        ) {
          return { error: "JSON-схема оценщика: ожидается JSON-объект" };
        }
        graders.push({ type, schema: schema as Record<string, unknown> });
        break;
      }
      case "llm_judge": {
        const parsed = parseRubric(get("rubric"));
        if ("error" in parsed) return parsed;
        graders.push({
          type,
          rubric: parsed.rubric,
          threshold: Number(get("threshold")),
          model: get(
            "model",
          ) as components["schemas"]["LlmJudgeGrader"]["model"],
        });
        break;
      }
    }
  }
  return { graders };
}

import { expect, test } from "vitest";
import { buildGraders, parseRubric } from "@/lib/graders";

function form(fields: Record<string, string>) {
  const f = new FormData();
  for (const [k, v] of Object.entries(fields)) f.set(k, v);
  return f;
}

test("buildGraders needs at least one grader", () => {
  expect(buildGraders([], form({}))).toEqual({
    error: "Добавьте хотя бы один оценщик",
  });
});

test("buildGraders reads exact and regex settings by row key", () => {
  const rows = [
    { key: 1, type: "exact" as const },
    { key: 4, type: "regex" as const },
  ];
  expect(
    buildGraders(
      rows,
      form({ "1.ignore_case": "on", "4.pattern": "^ok", "4.must_match": "on" }),
    ),
  ).toEqual({
    graders: [
      { type: "exact", ignore_case: true },
      { type: "regex", pattern: "^ok", must_match: true },
    ],
  });
  expect(
    buildGraders([{ key: 2, type: "regex" }], form({ "2.pattern": "x" })),
  ).toEqual({ graders: [{ type: "regex", pattern: "x", must_match: false }] });
});

test("buildGraders parses the json_schema and rejects non-objects", () => {
  const rows = [{ key: 1, type: "json_schema" as const }];
  expect(buildGraders(rows, form({ "1.schema": '{"type":"object"}' }))).toEqual(
    {
      graders: [{ type: "json_schema", schema: { type: "object" } }],
    },
  );
  expect(buildGraders(rows, form({ "1.schema": "{" }))).toEqual({
    error: "JSON-схема оценщика: некорректный JSON",
  });
  expect(buildGraders(rows, form({ "1.schema": "[1]" }))).toEqual({
    error: "JSON-схема оценщика: ожидается JSON-объект",
  });
});

test("buildGraders builds the judge from a rubric text", () => {
  const rows = [{ key: 7, type: "llm_judge" as const }];
  const out = buildGraders(
    rows,
    form({
      "7.rubric": "Тон | Вежливо ли\nТочность | Верны ли факты | 2",
      "7.threshold": "0.8",
      "7.model": "claude-haiku-5-5",
    }),
  );
  expect(out).toEqual({
    graders: [
      {
        type: "llm_judge",
        rubric: [
          { name: "Тон", description: "Вежливо ли", weight: 1 },
          { name: "Точность", description: "Верны ли факты", weight: 2 },
        ],
        threshold: 0.8,
        model: "claude-haiku-5-5",
      },
    ],
  });
});

test("parseRubric skips blank lines and names the bad line", () => {
  expect(parseRubric("\nТон | Вежливо ли\n\n  \n")).toEqual({
    rubric: [{ name: "Тон", description: "Вежливо ли", weight: 1 }],
  });
  expect(parseRubric("Тон | ok\nТолько название")).toEqual({
    error: "Рубрика, строка 2: ожидается «Название | Описание | вес»",
  });
  expect(parseRubric("Тон | ok | много")).toEqual({
    error: "Рубрика, строка 1: вес — число больше 0 и не больше 100",
  });
  expect(parseRubric("Тон | ok | 101")).toEqual({
    error: "Рубрика, строка 1: вес — число больше 0 и не больше 100",
  });
  expect(parseRubric("   \n")).toEqual({
    error: "Рубрика: нужен хотя бы один раздел",
  });
});

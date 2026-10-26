import { expect, test } from "vitest";
import { parseJsonl } from "@/lib/jsonl";

test("parseJsonl tolerates BOM/CRLF and reports line numbers", () => {
  const r = parseJsonl(
    '\uFEFF{"variables":{"t":"a"}}\r\n\r\n{"variables":{"t":5}}\n',
  );
  expect(r.cases).toHaveLength(1);
  expect(r.errors[0]).toMatch(/^Строка 3:/);
});

test("parseJsonl keeps variables and expected", () => {
  const r = parseJsonl(
    '{"variables":{"t":"a"},"expected":"A"}\n{"variables":{}}',
  );
  expect(r.errors).toEqual([]);
  expect(r.cases).toEqual([
    { variables: { t: "a" }, expected: "A" },
    { variables: {}, expected: null },
  ]);
});

test("parseJsonl rejects bad JSON, extra fields and non-string expected", () => {
  const r = parseJsonl(
    [
      '{"variables":',
      '{"variables":{},"x":1}',
      '{"variables":{},"expected":1}',
      "[]",
    ].join("\n"),
  );
  expect(r.cases).toEqual([]);
  expect(r.errors.map((e) => e.slice(0, 9))).toEqual([
    "Строка 1:",
    "Строка 2:",
    "Строка 3:",
    "Строка 4:",
  ]);
});

test("parseJsonl limits the number of cases like the API", () => {
  const r = parseJsonl('{"variables":{}}\n'.repeat(1001));
  expect(r.errors).toEqual(["В датасете не больше 1000 кейсов"]);
});

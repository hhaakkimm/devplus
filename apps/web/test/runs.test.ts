import { expect, test } from "vitest";
import {
  alignByPosition,
  deltaText,
  money,
  scoreText,
  statusText,
} from "@/lib/runs";

test("statusText covers every run status in Russian", () => {
  const run = { cases_done: 3, cases_total: 10 };
  expect(statusText({ ...run, status: "queued" })).toBe("В очереди");
  expect(statusText({ ...run, status: "running" })).toBe("Выполняется 3 из 10");
  expect(statusText({ ...run, status: "done" })).toBe("Готово");
  expect(statusText({ ...run, status: "failed" })).toBe("Ошибка");
  expect(statusText({ ...run, status: "over_budget" })).toBe(
    "Остановлен: превышен лимит",
  );
});

test("money formats the API's decimal strings", () => {
  expect(money("0.012300")).toBe("$0.0123");
  expect(money("5.000000", 2)).toBe("$5.00");
  expect(money("0")).toBe("$0.0000");
});

test("scoreText has two decimals and a dash for no score", () => {
  expect(scoreText(0.5)).toBe("0.50");
  expect(scoreText(1)).toBe("1.00");
  expect(scoreText(null)).toBe("—");
});

test("deltaText is B minus A with a sign, and a dash when a case is missing", () => {
  expect(deltaText(0.5, 0.75)).toBe("+0.25");
  expect(deltaText(0.75, 0.5)).toBe("-0.25");
  expect(deltaText(0.7, 0.5)).toBe("-0.20"); // 0.5 - 0.7 is -0.19999999999999996
  expect(deltaText(1, 1)).toBe("0.00");
  expect(deltaText(1, 0.999)).toBe("0.00"); // never "-0.00"
  expect(deltaText(undefined, 1)).toBe("—");
  expect(deltaText(1, undefined)).toBe("—");
});

test("alignByPosition pairs the cases of two runs by position", () => {
  const r = (position: number) => ({ position, score: 1, passed: true });
  const rows = alignByPosition([r(2), r(1)], [r(1), r(2), r(3)]);
  expect(rows.map((x) => x.position)).toEqual([1, 2, 3]);
  expect(rows[2].a).toBeUndefined();
  expect(rows[2].b?.position).toBe(3);
  expect(rows[0].a?.position).toBe(1);
});

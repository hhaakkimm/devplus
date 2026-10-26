import { expect, test, vi } from "vitest";
import {
  alignByPosition,
  deltaText,
  money,
  pollRun,
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

const run = (status: string) => ({
  data: { status },
  response: { status: 200 },
});
const failed = (status: number) => ({ response: { status } });
const poll = (answers: unknown[], signal = new AbortController().signal) => {
  const next = vi.fn(async () => {
    const a = answers.shift();
    if (a instanceof Error) throw a;
    return a as ReturnType<typeof run>;
  });
  const seen: string[] = [];
  const end = pollRun(next, (r) => seen.push(r.status), signal, 0);
  return { end, next, seen };
};

test("pollRun retries a 5xx and a dropped request, then refreshes once the run settles", async () => {
  const { end, next, seen } = poll([
    failed(502),
    run("running"),
    new TypeError("fetch failed"),
    failed(500),
    run("done"),
  ]);
  expect(await end).toBe("refresh");
  expect(next).toHaveBeenCalledTimes(5);
  expect(seen).toEqual(["running", "done"]);
});

test("pollRun hands 403 and 404 to the page, and 401 to sign-in", async () => {
  for (const [status, ended] of [
    [403, "refresh"],
    [404, "refresh"],
    [401, "sign-in"],
  ] as const) {
    const { end, next } = poll([failed(status), run("done")]);
    expect(await end).toBe(ended);
    expect(next).toHaveBeenCalledTimes(1);
  }
});

test("pollRun stops without asking when aborted", async () => {
  const stop = new AbortController();
  const { end, next } = poll([run("running")], stop.signal);
  stop.abort();
  expect(await end).toBe("stopped");
  expect(next).not.toHaveBeenCalled();
});

import fs from "node:fs";
import path from "node:path";
import { expect, type Page, test } from "@playwright/test";
import matter from "gray-matter";
import { draftKey, num, pct } from "@/lib/simulator";

// The browser context starts with an empty localStorage (no draft) and global-setup removes the
// e2e user's attempts, so the task starts clean. The api answers with EVALS_LLM_BACKEND=fake: the
// judge gets a canned verdict built from its schema (every section at the lowest score), so the
// naive scheme User → Server → Database ends «Не зачтено».
const TASK = "Сокращатель ссылок";
const DIR = path.join(
  process.cwd(),
  "../../content/10-system-design/simulator",
);

type Scenario = {
  visible: boolean;
  max_latency_ms: number;
  max_error_rate: number;
  max_message_loss?: number;
};
type Rubric = { description: string };

test.beforeEach(async ({ context }) => {
  await context.addCookies([
    {
      name: "session",
      value: process.env.E2E_SESSION_TOKEN!,
      domain: "localhost",
      path: "/",
    },
  ]);
});

const node = (page: Page, id: string) =>
  page.getByRole("group", { name: `Узел ${id}`, exact: true });
const edge = (page: Page, from: string, to: string) =>
  page.getByRole("group", { name: `Связь ${from} → ${to}`, exact: true });
const tab = (page: Page, name: string) => page.getByRole("tab", { name });
const panel = (page: Page, name: string) =>
  page.getByRole("tabpanel", { name });

// Drags from the source port of one node to the target port of another.
async function connect(page: Page, from: string, to: string) {
  const a = await node(page, from)
    .locator(".react-flow__handle.source")
    .boundingBox();
  const b = await node(page, to)
    .locator(".react-flow__handle.target")
    .boundingBox();
  if (!a || !b) throw new Error(`no ports for ${from} → ${to}`);
  await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
  await page.mouse.down();
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 10 });
  await page.mouse.up();
  await expect(edge(page, from, to)).toBeVisible();
}

// What the task keeps from the browser: the hidden scenarios' targets in the page's own number
// format, the reference notes and the rubric. Targets that the statement or an open scenario
// prints anyway are public.
function secrets(): string[] {
  const file = fs.readFileSync(path.join(DIR, "01-url-shortener.yaml"), "utf8");
  const statement = fs.readFileSync(
    path.join(DIR, "01-url-shortener.mdx"),
    "utf8",
  );
  const task = matter(`---\n${file}\n---\n`).data as {
    scenarios: Scenario[];
    review: { reference: string; rubric: Rubric[] };
  };
  const targets = (s: Scenario) => [
    `${num(s.max_latency_ms)} мс`,
    pct(s.max_error_rate),
    ...(s.max_message_loss ? [pct(s.max_message_loss)] : []),
  ];
  const open = new Set(
    task.scenarios.filter((s) => s.visible).flatMap(targets),
  );
  const hidden = task.scenarios
    .filter((s) => !s.visible)
    .flatMap(targets)
    .filter((t) => !open.has(t) && !statement.includes(t));
  return [
    ...new Set(hidden),
    ...task.review.reference.split("\n").filter((line) => line.trim()),
    ...task.review.rubric.map((r) => r.description),
  ];
}

test("the student builds a scheme, runs it, sends it and reads the attempts", async ({
  page,
}) => {
  test.setTimeout(90_000);
  // 1. the task list
  await page.goto("/simulator");
  await expect(
    page.getByRole("heading", { name: "Симулятор", level: 1 }),
  ).toBeVisible();
  await page.getByRole("link", { name: TASK }).click();
  await expect(
    page.getByRole("heading", { name: TASK, level: 1 }),
  ).toBeVisible();

  // an empty scheme: the run lists the structural errors, the submission answers 422
  const run = page.getByRole("button", { name: "Прогнать", exact: true });
  const send = page.getByRole("button", { name: "Отправить", exact: true });
  const results = panel(page, "Результаты");
  await run.click();
  await expect(results).toContainText("Схема не прогоняется");
  await send.click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Схема не прогоняется: " }),
  ).toBeVisible();

  // 2. User → Server → Database: nodes from the keyboard, edges with the mouse
  for (const label of ["Пользователи", "Сервер", "Database"]) {
    await page.getByRole("button", { name: label, exact: true }).focus();
    await page.keyboard.press("Enter");
  }
  await page.getByRole("button", { name: "Показать всю схему" }).click();
  await connect(page, "user-1", "server-1");
  await connect(page, "server-1", "database-1");

  await run.click();
  await expect(results).toBeVisible();
  await expect(results.getByText(/^✗/).first()).toBeVisible();
  await expect(results).toContainText("получает");
  await expect(results).toContainText("Средняя задержка:");
  await expect(results).toContainText("Ошибки:");
  // the switch colours the nodes by one scenario and labels them «λ / μ rps»
  await expect(node(page, "server-1")).toContainText("20 000 / 1 000 rps");
  await page
    .getByLabel("Сценарий на схеме")
    .selectOption({ label: "Всплеск ×2" });
  await expect(node(page, "server-1")).toContainText("40 000 / 1 000 rps");
  // a finding selects its node
  await results
    .getByRole("button", { name: /Один сервер без балансировщика/ })
    .click();
  await expect(node(page, "server-1")).toHaveClass(/selected/);

  // 3. the answers and the submission
  await tab(page, "Ответы").click();
  const answers = {
    "Требования и допущения": "Создать ссылку и перейти по ней.",
    "Оценка нагрузки": "20 000 rps, 95% чтений.",
    "Ключевые решения и компромиссы": "Один сервер, без кэша.",
  };
  for (const [label, text] of Object.entries(answers))
    await page.getByLabel(label, { exact: true }).fill(text);
  await expect(panel(page, "Ответы")).toContainText(
    `${answers["Оценка нагрузки"].length} / 5000`,
  );

  let release = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/simulator/tasks/*/*/attempts", async (route) => {
    if (route.request().method() === "POST") await held;
    await route.continue();
  });
  await send.click();
  await expect(send).toBeDisabled();
  await expect(run).toBeDisabled();
  await expect(page.getByText("Разбираем решение…")).toBeVisible();
  release();
  await expect(results.getByText("Не зачтено", { exact: true })).toBeVisible();
  await expect(send).toBeEnabled();
  await expect(results.getByText("скрытый", { exact: true })).toHaveCount(3);
  await expect(results.getByText(/^Балл: \d\.\d\d$/)).toBeVisible();
  await expect(
    results.getByRole("heading", { name: "AI-разбор" }),
  ).toBeVisible();

  // 4. the attempt in the history, its scheme read-only
  await tab(page, "Попытки").click();
  const rows = panel(page, "Попытки").getByRole("listitem");
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText("Не зачтено");
  await rows.first().getByRole("button").click();
  const back = page.getByRole("button", { name: "Вернуться к черновику" });
  await expect(back).toBeVisible();
  await expect(send).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Сервер", exact: true }),
  ).toHaveCount(0);
  await back.click();
  await expect(send).toBeVisible();

  // 5. nothing hidden reached the page. The fake judge writes its whole request, the reference
  // included, into every comment, so the judge's own text is left out of the check.
  const text = await page.evaluate(() => {
    const body = document.body.cloneNode(true) as HTMLElement;
    body.querySelector("#sim-review-h")?.closest("section")?.remove();
    return body.textContent ?? "";
  });
  const list = secrets();
  expect(list.length).toBeGreaterThanOrEqual(10);
  for (const secret of list) {
    const escaped = secret.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    // not a tail of a bigger number: «5%» is not in «95%», «200 мс» is not in «1 200 мс»
    const found = new RegExp(`(?<![\\d.,][\\s\\u00a0\\u202f]?)${escaped}`);
    expect(found.test(text), secret).toBe(false);
  }

  // 6. the draft survives a reload, once it is written: 500 ms after the last change
  const key = draftKey("system-design", "url-shortener");
  await expect
    .poll(() => page.evaluate((k) => localStorage.getItem(k), key))
    .toContain(answers["Ключевые решения и компромиссы"]);
  await page.reload();
  for (const id of ["user-1", "server-1", "database-1"])
    await expect(node(page, id)).toBeVisible();
  await expect(edge(page, "user-1", "server-1")).toBeVisible();
  await expect(edge(page, "server-1", "database-1")).toBeVisible();
  await tab(page, "Ответы").click();
  for (const [label, text] of Object.entries(answers))
    await expect(page.getByLabel(label, { exact: true })).toHaveValue(text);
  await tab(page, "Попытки").click();
  await expect(panel(page, "Попытки").getByRole("listitem")).toHaveCount(1);
});

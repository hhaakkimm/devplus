import fs from "node:fs";
import path from "node:path";
import { expect, type Page, test } from "@playwright/test";
import { origin } from "./worker";

// The e2e user and its data survive between runs, so names are fresh and checks are relative.
// The api and the worker answer with EVALS_LLM_BACKEND=fake: the critic gets a canned review
// built from its schema and the model echoes the rendered prompt.
const stamp = Date.now();

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

const VARIABLES_CHANGED =
  "Переписанная версия использует другие переменные — на текущих датасетах она не запустится";

async function review(page: Page, system: string, template: string) {
  await page.goto("/review");
  await expect(
    page.getByRole("heading", { name: "Ревью промпта", level: 1 }),
  ).toBeVisible();
  await expect(
    page.getByRole("radio", { name: "Вставить текст" }),
  ).toBeChecked();
  await page.getByLabel("Системный промпт").fill(system);
  await page.getByLabel("Шаблон сообщения").fill(template);
  await page.getByRole("button", { name: "Разобрать" }).click();
  await expect(page).toHaveURL(/\/review\/[0-9a-f-]{36}$/);
}

test("reviews free text and shows the checklist, the issues and the rewrite", async ({
  page,
}) => {
  await review(page, "Ты <b>редактор</b>.", "Исправь текст: {{text}}");
  await expect(
    page.getByRole("heading", { name: "Переписанная версия" }),
  ).toBeVisible();
  await expect(page.getByRole("rowheader")).toHaveText([
    "Цель",
    "Контекст",
    "Формат вывода",
    "Примеры",
    "Граничные случаи",
  ]);
  const issues = page.getByRole("region", { name: "Проблемы" });
  for (const severity of ["высокая", "средняя", "низкая"]) {
    await expect(issues).toContainText(severity);
  }
  // the original stands beside the rewrite, and prompt text is text
  await expect(
    page.getByRole("heading", { name: "Исходная", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Переписанная", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Ты <b>редактор</b>.").first()).toBeVisible();
  await expect(page.locator("main b")).toHaveCount(0);
  await expect(page.getByText(VARIABLES_CHANGED)).toHaveCount(0);
});

test("reviews a version of a prompt from the Lab", async ({ page }) => {
  const name = `Промпт ревью ${stamp}`;
  const template = "Перескажи {{text}} кратко";
  const created = await page.request.post("/api/evals/prompts", {
    data: {
      name,
      version: {
        system: "Ты редактор.",
        user_template: template,
        model: "claude-sonnet-5-5",
      },
    },
    headers: { Origin: origin },
  });
  expect(created.status(), await created.text()).toBe(201);

  await page.goto("/review");
  await page.getByRole("radio", { name: "Выбрать версию" }).check();
  await page
    .getByRole("combobox", { name: /^Промпт/ })
    .selectOption({ label: name });
  await page
    .getByRole("combobox", { name: /^Версия/ })
    .selectOption("Версия 1");
  await page.getByRole("button", { name: "Разобрать" }).click();
  await expect(page).toHaveURL(/\/review\/[0-9a-f-]{36}$/);
  await expect(
    page.getByRole("heading", { name: "Переписанная версия" }),
  ).toBeVisible();
  // the reviewed text is read from the version, nothing is added to the prompt yet
  await expect(
    page.getByRole("heading", { name: "Исходная", exact: true }).locator(".."),
  ).toContainText(template);
});

test("warns when the rewrite uses other variables and does not offer the check", async ({
  page,
}) => {
  // the fake rewrite echoes the whole request, so a variable in the system part is a new one
  await review(page, "Ты {{role}}.", "{{text}}");
  await expect(page.getByText(VARIABLES_CHANGED)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Проверить улучшение" }),
  ).toBeDisabled();
});

test("checks the rewrite on a dataset and opens the comparison", async ({
  page,
}) => {
  const name = `Датасет ревью ${stamp}`;
  // the API refuses a state-changing request that does not come from the app's origin
  const headers = { Origin: origin };
  const dataset = await page.request.post("/api/evals/datasets", {
    data: { name },
    headers,
  });
  expect(dataset.status(), await dataset.text()).toBe(201);
  const { id } = await dataset.json();
  const added = await page.request.post(`/api/evals/datasets/${id}/cases`, {
    data: { variables: { text: "кот" }, expected: "кот" },
    headers,
  });
  expect(added.status(), await added.text()).toBe(201);

  await review(page, "Ты редактор.", "Исправь текст: {{text}}");
  await page.getByRole("button", { name: "Проверить улучшение" }).click();
  const dialog = page.getByRole("dialog", { name: "Проверить улучшение" });
  await dialog
    .getByLabel("Датасет")
    .selectOption({ label: `${name} (кейсов: 1)` });
  await dialog.getByLabel("Тип оценщика").selectOption("exact");
  await dialog.getByRole("button", { name: "Добавить оценщик" }).click();
  await dialog.getByRole("button", { name: "Проверить", exact: true }).click();
  await expect(page).toHaveURL(
    /\/lab\/compare\?a=[0-9a-f-]{36}&b=[0-9a-f-]{36}$/,
  );
  await expect(
    page.getByRole("heading", { name: "Сравнение прогонов" }),
  ).toBeVisible();
});

// Trainer

const TASK = "Извлеки даты в ISO 8601";

async function openTask(page: Page) {
  await page.goto("/trainer");
  await expect(
    page.getByRole("heading", { name: "Тренажёр", level: 1 }),
  ).toBeVisible();
  await page.getByRole("link", { name: TASK }).click();
  await expect(
    page.getByRole("heading", { name: TASK, level: 1 }),
  ).toBeVisible();
  await expect(
    page.getByText("Модель: claude-haiku-5-5 · effort: low", { exact: true }),
  ).toBeVisible();
}

const history = (page: Page) =>
  page.getByRole("region", { name: "История попыток" }).getByRole("listitem");

// Sends a template with `{{text}}` and waits for the verdict of that very attempt: the history
// grows by one in the render that also puts the new attempt into the result block.
async function submit(page: Page) {
  await openTask(page);
  const before = await history(page).count();
  await page.getByLabel("Шаблон сообщения").fill("{{text}}");
  await page.getByRole("button", { name: "Отправить" }).click();
  await expect(history(page)).toHaveCount(before + 1);
  const result = page.getByRole("region", { name: "Результат" });
  await expect(result).toContainText("Не зачтено", { timeout: 15_000 });
  return result;
}

test("submits a template and shows the verdict without the cases", async ({
  page,
}) => {
  const result = await submit(page); // the fake answers with the echo, which is no date
  await expect(result).toContainText("Прошло кейсов: 0 из 6");
  await expect(result.getByText(/^Кейс 1: 0\.00/)).toBeVisible();
  await expect(result.getByText(/^Кейс 6: 0\.00/)).toBeVisible();
});

test("no hidden case reaches the page", async ({ page }) => {
  await submit(page);
  const dir = path.join(process.cwd(), "../../content/00-start/tasks");
  const yaml = fs.readFileSync(path.join(dir, "01-iso-dates.yaml"), "utf8");
  const statement = fs.readFileSync(path.join(dir, "01-iso-dates.mdx"), "utf8");
  // Every text and reference of the cases, except what the statement itself prints as an
  // example. The fake echoes the inputs, so a page that showed outputs would show them too.
  const secrets = [...yaml.split("cases:")[1].matchAll(/"([^"]+)"/g)]
    .map((m) => m[1])
    .filter((s) => !statement.includes(s));
  expect(secrets.length).toBeGreaterThanOrEqual(11);
  for (const secret of secrets) {
    await expect(page.locator("body")).not.toContainText(secret);
  }
});

test("the send button is disabled while the request is in flight", async ({
  page,
}) => {
  await openTask(page);
  const before = await history(page).count();
  const posts: string[] = [];
  await page.route("**/api/trainer/tasks/**/attempts", async (route) => {
    if (route.request().method() === "POST") {
      posts.push("POST");
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    await route.continue();
  });
  await page.getByLabel("Шаблон сообщения").fill("{{text}}");
  const send = page.getByRole("button", { name: "Отправить" });
  await send.click();
  await expect(send).toBeDisabled();
  await send.click({ force: true }); // a second click on the disabled button
  await expect(history(page)).toHaveCount(before + 1);
  await expect(send).toBeEnabled();
  expect(posts).toEqual(["POST"]);
});

test("a template without the task variable is refused with the API's text", async ({
  page,
}) => {
  await openTask(page);
  await page.getByLabel("Шаблон сообщения").fill("Дата");
  await page.getByRole("button", { name: "Отправить" }).click();
  await expect(page.getByText("В шаблоне нет переменных: text")).toBeVisible();
});

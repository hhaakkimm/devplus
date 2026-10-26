import { expect, test } from "@playwright/test";

// The e2e user and its prompts survive between runs, so every run uses fresh names.
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

async function createPrompt(
  page: import("@playwright/test").Page,
  name: string,
) {
  await page.goto("/lab");
  await expect(
    page.getByRole("heading", { name: "Лаборатория" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Новый промпт" }).click();
  await page.getByLabel("Название").fill(name);
  await page.getByLabel("Шаблон сообщения").fill("Скажи {{word}}");
  await expect(
    page.getByText("Переменные: word", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Создать промпт" }).click();
  await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
}

test("creates a prompt, shows its variables and saves a new version", async ({
  page,
}) => {
  await createPrompt(page, `Промпт ${stamp}`);
  await expect(
    page.getByText("Переменные: word", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Версия 1" })).toBeVisible();

  await page.getByLabel("Шаблон сообщения").fill("Скажи {{word}} и {{n}}");
  await expect(
    page.getByText("Переменные: word, n", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Сохранить как новую версию" })
    .click();
  await expect(page.getByRole("heading", { name: "Версия 2" })).toBeVisible();
});

test("save button is disabled while the request is in flight", async ({
  page,
}) => {
  await createPrompt(page, `Двойной клик ${stamp}`);
  const versionRequests: string[] = [];
  await page.route("**/api/evals/prompts/*/versions", async (route) => {
    versionRequests.push(route.request().method());
    await new Promise((resolve) => setTimeout(resolve, 1000));
    await route.continue();
  });

  const save = page.getByRole("button", { name: "Сохранить как новую версию" });
  await save.click();
  await expect(save).toBeDisabled();
  await save.click({ force: true }); // a second click on the disabled button
  await expect(page.getByRole("heading", { name: "Версия 2" })).toBeVisible();
  await expect(save).toBeEnabled();
  await expect(page.getByRole("heading", { name: /^Версия \d+$/ })).toHaveCount(
    2,
  );
  expect(versionRequests).toEqual(["POST"]);
});

test("creates a dataset, lists import errors, then imports two cases", async ({
  page,
}) => {
  const name = `Датасет ${stamp}`;
  await page.goto("/lab");
  await page.getByRole("link", { name: "Датасеты" }).click();
  await page.getByRole("link", { name: "Новый датасет" }).click();
  await page.getByLabel("Название").fill(name);
  await page.getByRole("button", { name: "Создать датасет" }).click();
  await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
  await expect(page.getByText("Кейсов пока нет.")).toBeVisible();

  async function chooseFile(content: string) {
    const chooser = page.waitForEvent("filechooser");
    await page.getByRole("button", { name: "Импорт JSONL" }).click();
    await (
      await chooser
    ).setFiles({
      name: "cases.jsonl",
      mimeType: "application/x-ndjson",
      buffer: Buffer.from(content),
    });
  }

  await chooseFile(
    '{"variables":{"word":"кот"}}\r\n\r\n{"variables":{"word":5}}\n',
  );
  await expect(
    page.getByRole("listitem").filter({ hasText: /^Строка 3:/ }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(0);

  await chooseFile(
    '﻿{"variables":{"word":"кот"},"expected":"cat"}\r\n{"variables":{"word":"пёс"}}\n',
  );
  await expect(page.getByText("В файле кейсов: 2.")).toBeVisible();
  await page.getByRole("button", { name: "Загрузить кейсы" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await expect(page.locator("tbody tr").first()).toContainText("кот");
  await expect(
    page.locator("tbody tr").first().locator("td").first(),
  ).toHaveText("1");

  await page.getByLabel("Переменные (JSON-объект)").fill('{"word":"рыба"}');
  await page.getByRole("button", { name: "Добавить кейс" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(3);
});

// Part 2: runs. The api and the worker run with EVALS_LLM_BACKEND=fake, which echoes the rendered prompt.

async function createDataset(
  page: import("@playwright/test").Page,
  name: string,
  jsonl: string,
) {
  await page.goto("/lab/datasets/new");
  await page.getByLabel("Название").fill(name);
  await page.getByRole("button", { name: "Создать датасет" }).click();
  await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Импорт JSONL" }).click();
  await (
    await chooser
  ).setFiles({
    name: "cases.jsonl",
    mimeType: "application/x-ndjson",
    buffer: Buffer.from(jsonl),
  });
  await page.getByRole("button", { name: "Загрузить кейсы" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(2);
}

async function openLauncher(
  page: import("@playwright/test").Page,
  dataset: string,
) {
  await page
    .getByRole("button", { name: "Запустить прогон", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Запустить прогон" });
  await dialog
    .getByLabel("Датасет")
    .selectOption({ label: `${dataset} (кейсов: 2)` });
  await dialog.getByLabel("Тип оценщика").selectOption("exact");
  await dialog.getByRole("button", { name: "Добавить оценщик" }).click();
  return dialog;
}

test("launches a run on the worker, shows its page and compares two runs", async ({
  page,
}) => {
  const dataset = `Датасет прогона ${stamp}`;
  await createDataset(
    page,
    dataset,
    '{"variables":{"word":"<i>кот</i>"},"expected":"Скажи пёс"}\n{"variables":{"word":"пёс"},"expected":"Скажи пёс"}\n',
  );
  await createPrompt(page, `Прогон ${stamp}`);
  const promptUrl = page.url();

  const dialog = await openLauncher(page, dataset);
  await dialog.getByRole("button", { name: "Оценить стоимость" }).click();
  await expect(
    dialog.getByText(/^Ожидаемая стоимость: \$\d+\.\d{4} \(лимит \$5\.00\)$/),
  ).toBeVisible();

  // a limit below the estimate is the API's 400, shown as it is
  await dialog.getByLabel("Лимит, $").fill("0.000001");
  await dialog.getByRole("button", { name: "Запустить", exact: true }).click();
  await expect(
    dialog.getByText(
      /^Ожидаемая стоимость \$\d+\.\d{2} превышает лимит \$0\.00$/,
    ),
  ).toBeVisible();
  await dialog.getByLabel("Лимит, $").fill("");

  // the launch button is disabled while the request is in flight, a second click sends nothing
  const posts: string[] = [];
  await page.route("**/api/evals/runs", async (route) => {
    posts.push(route.request().method());
    await new Promise((resolve) => setTimeout(resolve, 1000));
    await route.continue();
  });
  const launch = dialog.getByRole("button", { name: "Запустить", exact: true });
  await launch.click();
  await expect(launch).toBeDisabled();
  await launch.click({ force: true });
  await expect(page).toHaveURL(/\/lab\/runs\/[0-9a-f-]{36}$/);
  expect(posts).toEqual(["POST"]);
  await page.unroute("**/api/evals/runs");

  await expect(page.getByText("Готово", { exact: true })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText("Средний балл")).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(2);
  // case text is text: the tag shows up as characters and does not become an element
  await expect(page.getByText("Скажи <i>кот</i>")).toBeVisible();
  await expect(page.locator("tbody i")).toHaveCount(0);

  // a second run, then both on the comparison page through the form of the prompt page
  await page.goto(promptUrl);
  const second = await openLauncher(page, dataset);
  await second.getByRole("button", { name: "Запустить", exact: true }).click();
  await expect(page.getByText("Готово", { exact: true })).toBeVisible({
    timeout: 15_000,
  });
  await page.goto(promptUrl);
  await page.getByLabel("Прогон A").selectOption({ index: 1 });
  await page.getByLabel("Прогон B").selectOption({ index: 0 });
  await page.getByRole("button", { name: "Сравнить" }).click();
  await expect(page).toHaveURL(
    /\/lab\/compare\?a=[0-9a-f-]{36}&b=[0-9a-f-]{36}$/,
  );
  await expect(
    page.getByRole("heading", { name: "Сравнение прогонов" }),
  ).toBeVisible();
  await expect(page.getByRole("rowheader", { name: "Δ балла" })).toHaveCount(2);
});

test("a 401 from an action sends the user to sign-in", async ({ page }) => {
  await createPrompt(page, `Сессия ${stamp}`);
  await page.route("**/api/evals/prompts/*/versions", (route) =>
    route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
  );
  // the sign-in endpoint leads to GitHub: answer it here
  await page.route("**/api/auth/github/login", (route) =>
    route.fulfill({ status: 200, contentType: "text/html", body: "sign-in" }),
  );
  await page
    .getByRole("button", { name: "Сохранить как новую версию" })
    .click();
  await expect(page).toHaveURL(/\/api\/auth\/github\/login$/);
  await expect(page.getByText("Not authenticated")).toHaveCount(0);
});

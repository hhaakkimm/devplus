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

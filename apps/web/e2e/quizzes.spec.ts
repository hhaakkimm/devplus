import { expect, test, type Page } from "@playwright/test";

// Answers whatever question is on screen (the first option, in order) and moves on.
async function answerCurrent(page: Page) {
  const group = page.getByRole("group", { name: "Варианты ответа" });
  if (await group.isVisible()) {
    await group.getByRole("button").first().click();
  } else {
    const selects = page.getByRole("combobox");
    for (let i = 0, n = await selects.count(); i < n; i++) {
      await selects.nth(i).selectOption({ index: 1 });
    }
    await page.getByRole("button", { name: "Проверить" }).click();
  }
  await page.getByRole("button", { name: /^(Дальше|Завершить)$/ }).click();
}

async function finish(page: Page) {
  const result = page.getByRole("heading", { name: /^Результат: / });
  for (let i = 0; i < 40 && !(await result.isVisible()); i++) {
    await answerCurrent(page);
  }
  await expect(result).toBeVisible();
}

test("a quiz can be taken from the catalog, the best result is kept and mistakes can be repeated", async ({
  page,
  context,
}) => {
  await context.addCookies([
    {
      name: "session",
      value: process.env.E2E_SESSION_TOKEN!,
      domain: "localhost",
      path: "/",
    },
  ]);
  await page.goto("/quizzes");
  await expect(page.getByRole("heading", { name: "Квизы" })).toBeVisible();
  await page.goto("/quizzes/sd-prep/core-concepts");
  await expect(page.getByText(/^Вопрос 1 из \d+/)).toBeVisible();

  await finish(page);
  const heading = await page
    .getByRole("heading", { name: /^Результат: / })
    .innerText();
  const [, score, total] = heading.match(/(\d+) из (\d+)/)!;

  // the result reached the server: the catalog shows it after a fresh load
  await page.goto("/quizzes");
  await expect(
    page.getByText(`лучший результат ${score} из ${total}`).first(),
  ).toBeVisible();

  // repeating mistakes is practice: it neither needs the whole quiz nor changes the best result
  await page.goto("/quizzes/sd-prep/core-concepts");
  await finish(page);
  const repeat = page.getByRole("button", { name: "Повторить ошибки" });
  if (await repeat.isVisible()) {
    await repeat.click();
    await expect(page.getByText(/повтор ошибок/)).toBeVisible();
  }
});

test("an imported lesson renders its images and links to its quiz", async ({
  page,
  context,
}) => {
  await context.addCookies([
    {
      name: "session",
      value: process.env.E2E_SESSION_TOKEN!,
      domain: "localhost",
      path: "/",
    },
  ]);
  await page.goto("/lessons/core-concepts/caching");
  await expect(
    page.getByRole("heading", { name: "Caching", level: 1, exact: true }),
  ).toBeVisible();
  const img = page.locator("article img").first();
  await expect(img).toBeVisible();
  expect(
    await img.evaluate((i: HTMLImageElement) => i.naturalWidth),
  ).toBeGreaterThan(0);
  await page.getByRole("link", { name: /вопросов \d+/ }).click();
  await expect(page.getByText(/^Вопрос 1 из \d+/)).toBeVisible();
});

test("anonymous visitor is sent to GitHub login", async ({ page }) => {
  const res = await page.request.get("/quizzes", { maxRedirects: 0 });
  expect(res.status()).toBe(307);
  expect(res.headers()["location"]).toContain("/api/auth/github/login");
});

test("the language switch shows the English version without losing quiz progress", async ({
  page,
  context,
}) => {
  await context.addCookies([
    {
      name: "session",
      value: process.env.E2E_SESSION_TOKEN!,
      domain: "localhost",
      path: "/",
    },
  ]);
  await page.goto("/lessons/core-concepts/caching");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Caching");
  await page.getByRole("link", { name: "EN", exact: true }).click();
  await expect(page).toHaveURL(/\?lang=en$/);
  await expect(page.locator("[lang=en]").first()).toContainText("cache");
  await page.getByRole("link", { name: "RU", exact: true }).click();
  await expect(page).not.toHaveURL(/lang=/);

  await page.goto("/quizzes/core-concepts/caching");
  await answerCurrent(page);
  await expect(page.getByText("Вопрос 2 из")).toBeVisible();
  const ruQuestion = await page.getByRole("heading", { level: 2 }).innerText();
  await page.getByRole("link", { name: "EN", exact: true }).click();
  await expect(page).toHaveURL(/\?lang=en$/);
  await expect(page.getByText("Вопрос 2 из")).toBeVisible();
  await expect(page.getByRole("heading", { level: 2 })).not.toHaveText(
    ruQuestion,
  );
});

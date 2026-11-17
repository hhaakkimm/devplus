import { expect, test, type Page } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 } });

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

async function noHorizontalScroll(page: Page) {
  const { scrollWidth, clientWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
}

test("the programme fits a phone", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Программа" })).toBeVisible();
  await noHorizontalScroll(page);
});

test("a lesson reads and is marked done on a phone", async ({ page }) => {
  await page.goto("/lessons/ai-coding/fundamentals-planning-your-approach");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await noHorizontalScroll(page);
  const done = page.getByRole("button", { name: "Отметить пройденным" });
  await done.scrollIntoViewIfNeeded();
  await expect(done).toBeVisible();
  await done.click();
  await expect(
    page.getByRole("button", { name: "Снять отметку" }),
  ).toBeVisible();
});

test("a quiz can be answered on a phone", async ({ page }) => {
  await page.goto("/quizzes/core-concepts/caching");
  await expect(page.getByText(/^Вопрос 1 из \d+/)).toBeVisible();
  await noHorizontalScroll(page);
  const first = page
    .getByRole("group", { name: "Варианты ответа" })
    .getByRole("button")
    .first();
  await first.scrollIntoViewIfNeeded();
  await expect(first).toBeVisible();
  await first.click();
  await expect(
    page.getByRole("button", { name: /^(Дальше|Завершить)$/ }),
  ).toBeVisible();
});

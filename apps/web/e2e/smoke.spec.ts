import { expect, test } from "@playwright/test";

test("signed-in user opens a lesson and marks it done", async ({
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
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Программа" })).toBeVisible();
  const start = page.getByRole("region", { name: "Старт" });
  await expect(start.getByText("0 из 1", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Как пользоваться devplus" }).click();
  await page.getByRole("button", { name: "Отметить пройденным" }).click();
  await expect(
    page.getByRole("button", { name: "Снять отметку" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "← К программе" }).click();
  await expect(start.getByText("1 из 1", { exact: true })).toBeVisible();
});

test("the lesson page shows where you are in the programme", async ({
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
  await page.goto("/lessons/ai-coding/fundamentals-planning-your-approach");
  const menu = page.getByRole("navigation", { name: "Программа" });
  await expect(
    menu.getByRole("link", { name: "Планирование подхода" }),
  ).toHaveAttribute("aria-current", "page");
  // The current module is open and split into subsections; the others are folded.
  await expect(menu.getByText("Основы", { exact: true })).toBeVisible();
  await expect(menu.getByText("Паттерны", { exact: true })).toBeVisible();
  await expect(
    menu.getByRole("link", { name: "Как пользоваться devplus" }),
  ).toBeHidden();
  // A click in the menu moves to that lesson and the highlight follows.
  await menu.getByRole("link", { name: "Коммуникация" }).click();
  await expect(page).toHaveURL(/fundamentals-communication$/);
  await expect(
    page
      .getByRole("navigation", { name: "Программа" })
      .getByRole("link", { name: "Коммуникация" }),
  ).toHaveAttribute("aria-current", "page");
});

test("the programme splits a module into subsections", async ({
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
  await page.goto("/");
  const ai = page.getByRole("region", { name: "AI coding интервью" });
  await ai.getByRole("button").first().click(); // long modules start folded
  for (const title of ["Обзор", "Основы", "Паттерны", "Разборы задач"]) {
    await expect(
      ai.getByRole("heading", { level: 3, name: title }),
    ).toBeVisible();
  }
});

test("anonymous visitor is sent to GitHub login", async ({ page }) => {
  const res = await page.request.get("/", { maxRedirects: 0 });
  expect(res.status()).toBe(307);
  expect(res.headers()["location"]).toContain("/api/auth/github/login");
});

test("no-access page offers GitHub login", async ({ page }) => {
  await page.goto("/no-access");
  await expect(
    page.getByRole("heading", { name: "Нет доступа" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Войти через GitHub" }),
  ).toHaveAttribute("href", "/api/auth/github/login");
});

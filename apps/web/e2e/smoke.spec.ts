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
  await expect(page.getByText("0 из 1")).toBeVisible();
  await page.getByRole("link", { name: "Как пользоваться devplus" }).click();
  await page.getByRole("button", { name: "Отметить пройденным" }).click();
  await expect(
    page.getByRole("button", { name: "Снять отметку" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "← К программе" }).click();
  await expect(page.getByText("1 из 1")).toBeVisible();
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

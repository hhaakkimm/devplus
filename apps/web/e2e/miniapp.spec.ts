import { expect, test } from "@playwright/test";

const miniApp = { name: "miniapp", value: "1", domain: "localhost", path: "/" };

test("no session inside the Mini App goes to /tg, not GitHub", async ({
  page,
  context,
}) => {
  await context.addCookies([miniApp]);
  await page.goto("/");
  // The /tg page itself arrives later; only the destination matters here.
  await expect(page).toHaveURL(/\/tg$/);
});

test("the Mini App hides the logout button", async ({ page, context }) => {
  await context.addCookies([
    {
      name: "session",
      value: process.env.E2E_SESSION_TOKEN!,
      domain: "localhost",
      path: "/",
    },
    miniApp,
  ]);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Программа" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Выйти" })).toHaveCount(0);
});

test("the browser shows the logout button", async ({ page, context }) => {
  await context.addCookies([
    {
      name: "session",
      value: process.env.E2E_SESSION_TOKEN!,
      domain: "localhost",
      path: "/",
    },
  ]);
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Выйти" })).toBeVisible();
});

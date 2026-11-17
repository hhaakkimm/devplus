import { expect, test } from "@playwright/test";

const miniApp = { name: "miniapp", value: "1", domain: "localhost", path: "/" };

test("/tg outside Telegram offers the usual login and drops the Mini App cookie", async ({
  page,
  context,
}) => {
  await context.addCookies([miniApp]);
  await page.goto("/tg");
  await expect(page.getByText("Открой приложение из Telegram")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Обычный вход" }),
  ).toHaveAttribute("href", "/api/auth/github/login");
  const cookies = await context.cookies();
  expect(cookies.find((c) => c.name === "miniapp")).toBeUndefined();
});

test("/tg/linked tells to go back to Telegram", async ({ page }) => {
  await page.goto("/tg/linked");
  await expect(page.getByText("Готово, вернись в Telegram")).toBeVisible();
});

test("/tg/link-failed explains the reason", async ({ page }) => {
  await page.goto("/tg/link-failed?reason=invalid");
  await expect(page.getByText("Ссылка устарела")).toBeVisible();
});

test("/tg/confirm without a link request shows an error", async ({ page }) => {
  await page.goto("/tg/confirm");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("button", { name: "Привязать" })).toHaveCount(0);
});

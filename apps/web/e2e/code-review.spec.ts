import { expect, type Page, test } from "@playwright/test";

// The e2e user and its attempt at the task survive between runs, so the test starts by bringing
// the page to an empty draft. The api answers with EVALS_LLM_BACKEND=fake: the judge gets a
// canned verdict built from its schema (every rubric section, lowest score), so the result is a
// fail; the test checks that the result view appears, not what it says.
const TASK = "Цикл LLM-агента с инструментами";

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

const heading = (page: Page, name: string) =>
  page.getByRole("heading", { name, exact: true });

// A graded or failed attempt from an earlier run gives way to a new draft; leftover comments are
// removed. (A leftover `grading` attempt would only clear after the 10 minute grading timeout.)
async function emptyDraft(page: Page) {
  const retry = page.getByRole("button", {
    name: /^(Попробовать снова|Начать заново)$/,
  });
  const remove = page.getByRole("button", { name: "Удалить" });
  await expect(
    retry.or(heading(page, "Замечания (0)")).or(remove.first()).first(),
  ).toBeVisible();
  if (await retry.isVisible()) {
    await retry.click();
    await expect(retry).toBeHidden();
  }
  while ((await remove.count()) > 0) await remove.first().click();
  await expect(heading(page, "Замечания (0)")).toBeVisible();
}

test("the student reviews the code, sends it, reads the result and retries", async ({
  page,
}) => {
  // the sending waits up to 30 s for the judge; a cold `pnpm dev` compiles the pages on top of that
  test.setTimeout(90_000);
  // list
  await page.goto("/code-review");
  await expect(
    page.getByRole("heading", { name: "Code Review", level: 1 }),
  ).toBeVisible();
  const row = page.getByRole("row", { name: new RegExp(TASK) });
  await expect(row).toContainText(/Не начата|Попытка|Зачёт/);
  await page.getByRole("link", { name: TASK }).click();

  // task page: statement and the file tree
  await expect(
    page.getByRole("heading", { name: TASK, level: 1 }),
  ).toBeVisible();
  await expect(page.getByText("Условие", { exact: true })).toBeVisible();
  const files = page.getByRole("navigation", { name: "Файлы" });
  for (const file of ["agent.py", "tools.py", "memory.py", "llm.py"])
    await expect(files.getByRole("button", { name: file })).toBeVisible();
  await emptyDraft(page);

  // a comment on lines 18-20 of agent.py: click, shift-click, text, save
  await files.getByRole("button", { name: "agent.py" }).click();
  await page.getByRole("button", { name: "Строка 18", exact: true }).click();
  await page
    .getByRole("button", { name: "Строка 20", exact: true })
    .click({ modifiers: ["Shift"] });
  const text = "Цикл без предела числа шагов: нужен MAX_STEPS";
  const field = page.getByLabel(/^Замечание к/);
  await field.fill(text);
  // Shift+click again moves the range of the same comment; the typed text stays
  await page
    .getByRole("button", { name: "Строка 21", exact: true })
    .click({ modifiers: ["Shift"] });
  await expect(page.getByText("agent.py:18–21", { exact: true })).toBeVisible();
  await expect(field).toHaveValue(text);
  await page
    .getByRole("button", { name: "Строка 20", exact: true })
    .click({ modifiers: ["Shift"] });
  await expect(page.getByText("agent.py:18–20", { exact: true })).toBeVisible();
  await expect(field).toHaveValue(text);
  await page.getByRole("button", { name: "Добавить замечание" }).click();
  await expect(heading(page, "Замечания (1)")).toBeVisible();
  const comments = page.getByRole("region", { name: /^Замечания/ });
  await expect(comments).toContainText("agent.py:18–20");
  await expect(comments).toContainText(text);
  await expect(
    page.getByRole("button", { name: "Строка 19, есть замечание" }),
  ).toBeVisible();

  // verdict and summary; autosave, and the draft survives a reload
  await page
    .getByRole("radio", { name: "Запросить правки (request changes)" })
    .check();
  await page.getByLabel("Резюме").fill("Нужны правки: цикл не ограничен.");
  await expect(page.getByText("Сохранено", { exact: true })).toBeVisible();
  await page.reload();
  await expect(heading(page, "Замечания (1)")).toBeVisible();
  await expect(page.getByRole("region", { name: /^Замечания/ })).toContainText(
    text,
  );
  await expect(
    page.getByRole("radio", { name: "Запросить правки (request changes)" }),
  ).toBeChecked();
  await expect(page.getByLabel("Резюме")).toHaveValue(
    "Нужны правки: цикл не ограничен.",
  );

  // send; the fake judge is instant, the page refresh is not
  await page.getByRole("button", { name: "Отправить", exact: true }).click();
  await expect(heading(page, "Проблемы в коде")).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText(/^(Зачёт|Не зачтено)$/).first()).toBeVisible();
  await expect(heading(page, "Результат")).toBeVisible();
  // the issues are revealed with their descriptions, the traps and the judge's sections follow
  const issues = page.locator("#issues-h + ul > li");
  await expect(issues.first()).toContainText("agent.py:18");
  await expect(issues.first()).toContainText(
    "выходит только когда модель сама перестала вызывать инструменты",
  );
  await expect(page.getByText(/^(найдена|пропущена)$/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /^Ловушки/ })).toBeVisible();
  await expect(heading(page, "Общая оценка")).toBeVisible();
  // the editing is gone from a graded attempt, but the code and the student's own comment stay
  await expect(page.getByLabel("Резюме")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Отправить", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Код agent.py" }),
  ).toContainText("def ");
  await expect(page.getByRole("region", { name: /^Замечания/ })).toContainText(
    text,
  );
  await expect(page.getByRole("button", { name: "Удалить" })).toHaveCount(0);

  // a bad-review report
  await page.getByText("Сообщить о плохом разборе").click();
  await page.getByLabel("Что не так").fill("Судья не заметил моё замечание");
  await page.getByRole("button", { name: "Отправить жалобу" }).click();
  await expect(page.getByText("Спасибо, жалоба отправлена.")).toBeVisible();

  // retry: a fresh, empty workspace
  await page.getByRole("button", { name: "Попробовать снова" }).click();
  await expect(heading(page, "Замечания (0)")).toBeVisible();
  await expect(heading(page, "Проблемы в коде")).toHaveCount(0);
  await expect(page.getByLabel("Резюме")).toHaveValue("");
  await expect(
    page.getByRole("radio", { name: "Запросить правки (request changes)" }),
  ).not.toBeChecked();
});

import { compile } from "@mdx-js/mdx";
import { expect, test } from "vitest";
import { headingIds, type TocItem } from "@/lib/toc";

test("headings get stable ids and land in the table of contents", async () => {
  const toc: TocItem[] = [];
  const source = [
    "# Title is not listed",
    "## Нефункциональные [требования](/lessons/a/b)",
    "### `code` and *emphasis*",
    "## Нефункциональные требования",
    "```\n## not a heading\n```",
    "#### too deep",
  ].join("\n\n");
  const js = String(
    await compile(source, { remarkPlugins: [headingIds(toc)] }),
  );
  expect(toc).toEqual([
    {
      level: 2,
      text: "Нефункциональные требования",
      id: "нефункциональные-требования",
    },
    { level: 3, text: "code and emphasis", id: "code-and-emphasis" },
    {
      level: 2,
      text: "Нефункциональные требования",
      id: "нефункциональные-требования-2",
    },
  ]);
  expect(js).toContain("нефункциональные-требования-2");
});

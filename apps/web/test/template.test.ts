import { expect, test } from "vitest";
import { templateVariables } from "@/lib/template";

test("templateVariables matches API rules", () => {
  expect(templateVariables("Hi {{ name }} {{x1}} {{1bad}}")).toEqual([
    "name",
    "x1",
  ]);
});

test("templateVariables lists each name once, in order of appearance", () => {
  expect(templateVariables("{{b}} {{a}} {{b}}")).toEqual(["b", "a"]);
});

test("templateVariables treats whitespace like Python's \\s", () => {
  expect(templateVariables("{{\x1Cname\x85}} {{﻿no}} {{ ok　}}")).toEqual([
    "name",
    "ok",
  ]);
});

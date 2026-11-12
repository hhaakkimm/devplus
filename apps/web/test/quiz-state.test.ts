import { expect, test } from "vitest";
import {
  canCheck,
  initialAnswer,
  isCorrect,
  type Question,
} from "@/lib/quiz-state";

const base = { level: "mid", question: "?", explanation: "!" } as const;
const tf: Question = { ...base, type: "true_false", answer: true };
const choice: Question = {
  ...base,
  type: "choice",
  options: ["a", "b", "c", "d"],
  answer: 2,
};
const ranking: Question = {
  ...base,
  type: "ranking",
  items: ["x", "y", "z"],
  answer: [1, 2, 0],
};
const matching: Question = {
  ...base,
  type: "matching",
  left: ["l0", "l1", "l2"],
  right: ["r0", "r1", "r2"],
  answer: [2, 0, 1],
};

test("true_false and choice compare the chosen value", () => {
  expect(isCorrect(tf, true)).toBe(true);
  expect(isCorrect(tf, false)).toBe(false);
  expect(isCorrect(choice, 2)).toBe(true);
  expect(isCorrect(choice, 1)).toBe(false);
});

test("ranking and matching compare the whole array", () => {
  expect(isCorrect(ranking, [1, 2, 0])).toBe(true);
  expect(isCorrect(ranking, [1, 0, 2])).toBe(false);
  expect(isCorrect(matching, [2, 0, 1])).toBe(true);
  expect(isCorrect(matching, [2, 1, 0])).toBe(false);
});

test("an answer of the wrong shape is simply wrong", () => {
  expect(isCorrect(choice, null)).toBe(false);
  expect(isCorrect(tf, null)).toBe(false);
  expect(isCorrect(matching, [2, 0, -1])).toBe(false);
});

test("canCheck needs a choice, and every pair for matching", () => {
  expect(canCheck(tf, null)).toBe(false);
  expect(canCheck(tf, false)).toBe(true);
  expect(canCheck(choice, 0)).toBe(true);
  expect(canCheck(ranking, initialAnswer(ranking))).toBe(true);
  expect(canCheck(matching, initialAnswer(matching))).toBe(false);
  expect(canCheck(matching, [2, 0, 1])).toBe(true);
});

test("a ranking never starts already solved", () => {
  const solved: Question = { ...ranking, answer: [0, 1, 2] };
  expect(initialAnswer(solved)).not.toEqual([0, 1, 2]);
  expect(initialAnswer(ranking)).not.toEqual([1, 2, 0]);
  expect([...(initialAnswer(ranking) as number[])].sort()).toEqual([0, 1, 2]);
});

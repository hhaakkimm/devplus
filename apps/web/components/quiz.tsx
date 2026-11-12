"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { apiDetail, browserApi } from "@/lib/browser-api";
import {
  canCheck,
  initialAnswer,
  isCorrect,
  type Answer,
  type Level,
  type Question,
  type Quiz,
} from "@/lib/quiz-state";

const LEVEL_LABEL: Record<Level, string> = {
  junior: "Junior",
  mid: "Middle",
  senior: "Senior",
  staff: "Staff",
};

const OK =
  "border-green-600 bg-green-50 text-green-900 dark:bg-green-950 dark:text-green-100";
const BAD =
  "border-red-600 bg-red-50 text-red-900 dark:bg-red-950 dark:text-red-100";

// What to show as "the right answer" once a question is checked.
function rightAnswer(q: Question): string[] {
  switch (q.type) {
    case "true_false":
      return [q.answer ? "Верно" : "Неверно"];
    case "choice":
      return [q.options[q.answer]];
    case "ranking":
      return q.answer.map((i, n) => `${n + 1}. ${q.items[i]}`);
    case "matching":
      return q.left.map((l, i) => `${l} → ${q.right[q.answer[i]]}`);
  }
}

function QuestionBody({
  q,
  answer,
  setAnswer,
  checked,
}: {
  q: Question;
  answer: Answer;
  setAnswer: (a: Answer) => void;
  checked: boolean;
}) {
  if (q.type === "true_false" || q.type === "choice") {
    const options =
      q.type === "choice"
        ? q.options.map((label, value) => ({ label, value }))
        : [
            { label: "Верно", value: true },
            { label: "Неверно", value: false },
          ];
    return (
      <div role="group" aria-label="Варианты ответа" className="space-y-2">
        {options.map((o) => {
          const picked = answer === o.value;
          const right = checked && o.value === q.answer;
          const wrong = checked && picked && !right;
          return (
            <button
              key={o.label}
              type="button"
              disabled={checked}
              aria-pressed={picked}
              className={`flex w-full items-start gap-3 rounded-lg border px-4 py-3 text-left transition-colors ${
                right
                  ? OK
                  : wrong
                    ? BAD
                    : checked
                      ? "opacity-60"
                      : "hover:border-foreground/40 hover:bg-muted"
              }`}
              onClick={() => setAnswer(o.value)}
            >
              <span className="flex-1">{o.label}</span>
              {right && <span aria-hidden>✓</span>}
              {wrong && <span aria-hidden>✗</span>}
            </button>
          );
        })}
      </div>
    );
  }
  if (q.type === "ranking") {
    const order = answer as number[];
    const move = (from: number, to: number) => {
      const next = [...order];
      [next[from], next[to]] = [next[to], next[from]];
      setAnswer(next);
    };
    return (
      <ol className="space-y-2" aria-label="Расставь по порядку">
        {order.map((item, pos) => (
          <li
            key={item}
            className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${
              checked ? (item === q.answer[pos] ? OK : BAD) : ""
            }`}
          >
            <span className="w-6 text-muted-foreground">{pos + 1}.</span>
            <span className="flex-1">{q.items[item]}</span>
            <Button
              variant="outline"
              size="sm"
              disabled={checked || pos === 0}
              aria-label={`Поднять: ${q.items[item]}`}
              onClick={() => move(pos, pos - 1)}
            >
              ↑
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={checked || pos === order.length - 1}
              aria-label={`Опустить: ${q.items[item]}`}
              onClick={() => move(pos, pos + 1)}
            >
              ↓
            </Button>
          </li>
        ))}
      </ol>
    );
  }
  const chosen = answer as number[];
  return (
    <ul className="space-y-3">
      {q.left.map((label, i) => (
        <li key={label} className="space-y-1">
          <label htmlFor={`match-${i}`}>{label}</label>
          <select
            id={`match-${i}`}
            value={chosen[i]}
            disabled={checked}
            className={`block w-full rounded-lg border bg-background px-3 py-2 ${
              checked ? (chosen[i] === q.answer[i] ? OK : BAD) : ""
            }`}
            onChange={(e) =>
              setAnswer(
                chosen.map((v, j) => (j === i ? Number(e.target.value) : v)),
              )
            }
          >
            <option value={-1}>Выбери соответствие</option>
            {q.right.map((r, j) => (
              <option key={r} value={j}>
                {r}
              </option>
            ))}
          </select>
        </li>
      ))}
    </ul>
  );
}

export function QuizRunner({ quiz }: { quiz: Quiz }) {
  const all = quiz.questions.map((_, i) => i);
  const [queue, setQueue] = useState(all);
  const [fullPass, setFullPass] = useState(true);
  const [pos, setPos] = useState(0);
  const [answer, setAnswer] = useState<Answer>(() =>
    initialAnswer(quiz.questions[0]),
  );
  const [checked, setChecked] = useState(false);
  const [wrong, setWrong] = useState<number[]>([]);
  const [done, setDone] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  function begin(next: number[], full: boolean) {
    setQueue(next);
    setFullPass(full);
    setPos(0);
    setAnswer(initialAnswer(quiz.questions[next[0]]));
    setChecked(false);
    setWrong([]);
    setDone(false);
    setSaveError(null);
  }

  async function save(score: number, total: number) {
    const { response, error } = await browserApi.PUT(
      "/api/quizzes/{module}/{quiz}/result",
      {
        params: { path: { module: quiz.moduleSlug, quiz: quiz.quizSlug } },
        body: { score, total },
      },
    );
    if (!response.ok) setSaveError(apiDetail(error, response.status));
  }

  const index = queue[pos];
  const q = quiz.questions[index];
  const correct = checked && isCorrect(q, answer);

  function pick(a: Answer) {
    setAnswer(a);
    // A single tap answers true/false and choice questions at once.
    if (q.type === "true_false" || q.type === "choice") setChecked(true);
  }

  function next() {
    const nextWrong = correct ? wrong : [...wrong, index];
    setWrong(nextWrong);
    if (pos + 1 < queue.length) {
      setPos(pos + 1);
      setAnswer(initialAnswer(quiz.questions[queue[pos + 1]]));
      setChecked(false);
      return;
    }
    setDone(true);
    // Only a full pass is a result; repeating mistakes is practice and is not recorded.
    if (fullPass) void save(queue.length - nextWrong.length, queue.length);
  }

  if (done) {
    const score = queue.length - wrong.length;
    return (
      <section aria-labelledby="quiz-result">
        <h2 id="quiz-result" className="text-2xl font-semibold">
          Результат: {score} из {queue.length}
        </h2>
        {saveError && (
          <p role="alert" className="mt-2 text-destructive">
            Результат не сохранился: {saveError}
          </p>
        )}
        {wrong.length > 0 && (
          <>
            <h3 className="mt-6 font-semibold">Ошибки</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {wrong.map((i) => (
                <li key={i}>{quiz.questions[i].question}</li>
              ))}
            </ul>
          </>
        )}
        <div className="mt-6 flex flex-wrap gap-3">
          {wrong.length > 0 && (
            <Button onClick={() => begin(wrong, false)}>
              Повторить ошибки
            </Button>
          )}
          <Button variant="outline" onClick={() => begin(all, true)}>
            Пройти заново
          </Button>
          <Link
            href="/quizzes"
            className="inline-flex items-center hover:underline"
          >
            ← Все квизы
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Вопрос">
      <div
        role="progressbar"
        aria-label="Прогресс квиза"
        aria-valuemin={0}
        aria-valuemax={queue.length}
        aria-valuenow={pos}
        className="h-1.5 overflow-hidden rounded-full bg-muted"
      >
        <div
          className="h-full bg-foreground transition-all"
          style={{ width: `${(pos / queue.length) * 100}%` }}
        />
      </div>
      <p className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
        <span>
          Вопрос {pos + 1} из {queue.length}
          {!fullPass && " · повтор ошибок"}
        </span>
        <span className="rounded-full border px-2 py-0.5 text-xs">
          {LEVEL_LABEL[q.level]}
        </span>
      </p>
      <h2 className="mt-3 text-xl font-semibold leading-snug">{q.question}</h2>
      <div className="mt-4">
        <QuestionBody
          q={q}
          answer={answer}
          setAnswer={pick}
          checked={checked}
        />
      </div>
      {!checked && (q.type === "ranking" || q.type === "matching") && (
        <Button
          className="mt-4"
          disabled={!canCheck(q, answer)}
          onClick={() => setChecked(true)}
        >
          Проверить
        </Button>
      )}
      {checked && (
        <div role="status" className="mt-5 space-y-4">
          <div className={`rounded-lg border p-4 ${correct ? OK : BAD}`}>
            <p className="font-semibold">{correct ? "Верно!" : "Неверно"}</p>
            {!correct && (
              <div className="mt-2">
                <p className="text-sm">Верный ответ:</p>
                <ul className="list-none space-y-1 font-medium">
                  {rightAnswer(q).map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <p className="leading-relaxed text-muted-foreground">
            {q.explanation}
          </p>
          <Button onClick={next}>
            {pos + 1 < queue.length ? "Дальше" : "Завершить"}
          </Button>
        </div>
      )}
    </section>
  );
}

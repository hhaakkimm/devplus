import { scoreText } from "@/lib/runs";
import {
  msText,
  pct,
  type Attempt,
  type Finding,
  type RunOut,
} from "@/lib/simulator";

// The last «Прогнать» (open scenarios with numbers) or an attempt (every scenario's verdict and
// the AI review). A hidden scenario comes only as id, title, verdict and explanation.
export type Result = { run: RunOut } | { attempt: Attempt };

const SEVERITY = { critical: "Критично", warning: "Предупреждение" };
const text = "break-words whitespace-pre-wrap";

const mark = (passed: boolean) => (passed ? "✓" : "✗");

function Findings({
  findings,
  onFocus,
}: {
  findings: Finding[];
  onFocus: (nodeId: string) => void;
}) {
  if (findings.length === 0) return null;
  return (
    <section aria-labelledby="sim-findings-h">
      <h3 id="sim-findings-h" className="font-semibold">
        Находки
      </h3>
      <ul className="mt-2 grid gap-2 text-sm">
        {findings.map((f, i) => {
          const label = `${SEVERITY[f.severity]}: ${f.message}`;
          const tone = f.severity === "critical" ? "text-destructive" : "";
          return (
            <li key={i}>
              {f.node_id ? (
                // selects the node and centres the canvas on it
                <button
                  type="button"
                  className={`text-left underline decoration-dotted underline-offset-4 hover:decoration-solid ${tone}`}
                  onClick={() => onFocus(f.node_id!)}
                >
                  {label} ({f.node_id})
                </button>
              ) : (
                <span className={tone}>{label}</span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function RunResults({
  run,
  onFocus,
}: {
  run: RunOut;
  onFocus: (nodeId: string) => void;
}) {
  if (run.structural_errors.length > 0)
    return (
      <section aria-labelledby="sim-errors-h">
        <h3 id="sim-errors-h" className="font-semibold">
          Схема не прогоняется
        </h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-destructive">
          {run.structural_errors.map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      </section>
    );
  return (
    <>
      <ul className="grid gap-4">
        {run.scenarios.map((s) => (
          <li key={s.id} className="grid gap-1 text-sm">
            <p className="font-medium">
              {mark(s.passed)} {s.title}
            </p>
            <p>Средняя задержка: {msText(s.latency_ms)}</p>
            <p>Ошибки: {pct(s.error_rate)}</p>
            {s.message_loss > 0 && (
              <p>Потеряно сообщений: {pct(s.message_loss)}</p>
            )}
            {s.bottleneck && <p>Узкое место: {s.bottleneck}</p>}
            <p className="text-muted-foreground">{s.explanation}</p>
          </li>
        ))}
      </ul>
      <Findings findings={run.findings} onFocus={onFocus} />
    </>
  );
}

function AttemptResult({
  attempt,
  onFocus,
}: {
  attempt: Attempt;
  onFocus: (nodeId: string) => void;
}) {
  const { review } = attempt;
  return (
    <>
      <p className="flex flex-wrap items-center gap-3">
        <span
          className={`rounded-full px-2 py-0.5 text-sm font-medium ${attempt.passed ? "bg-green-600/15 text-green-700 dark:text-green-400" : "bg-destructive/15 text-destructive"}`}
        >
          {attempt.passed ? "Зачтено" : "Не зачтено"}
        </span>
        {attempt.score != null && <span>Балл: {scoreText(attempt.score)}</span>}
      </p>
      {attempt.review_error && (
        <p role="alert" className="text-sm text-destructive">
          {attempt.review_error}
        </p>
      )}
      <section aria-labelledby="sim-verdicts-h">
        <h3 id="sim-verdicts-h" className="font-semibold">
          Сценарии
        </h3>
        <ul className="mt-2 grid gap-3 text-sm">
          {attempt.scenarios.map((s) => (
            <li key={s.id}>
              <p className="font-medium">
                {mark(s.passed)} {s.title}
                {!s.visible && (
                  <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-xs font-normal">
                    скрытый
                  </span>
                )}
              </p>
              <p className="text-muted-foreground">{s.explanation}</p>
            </li>
          ))}
        </ul>
      </section>
      <Findings findings={attempt.findings} onFocus={onFocus} />
      {review && (
        <section aria-labelledby="sim-review-h">
          <h3 id="sim-review-h" className="font-semibold">
            AI-разбор
          </h3>
          <ul className="mt-2 grid gap-3 text-sm">
            {review.sections.map((s) => (
              <li key={s.name}>
                <p className="font-medium">
                  {s.name}: {s.score} из 5
                </p>
                <p className={`text-muted-foreground ${text}`}>{s.comment}</p>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-sm font-medium">Общий вывод</p>
          <p className={`text-sm ${text}`}>{review.comment}</p>
        </section>
      )}
    </>
  );
}

export function Results({
  result,
  stale = false,
  onFocus,
}: {
  result: Result | null;
  stale?: boolean; // the scheme was edited after this result
  onFocus: (nodeId: string) => void;
}) {
  if (!result)
    return (
      <p className="text-sm text-muted-foreground">
        Нажми «Прогнать», чтобы проверить схему на открытых сценариях.
      </p>
    );
  return (
    <div className="grid gap-6">
      {stale && (
        <p role="status" className="rounded-lg border p-3 text-sm">
          {"run" in result
            ? "Схема изменилась — нажми «Прогнать»"
            : "Результат относится к отправленной схеме"}
        </p>
      )}
      {"run" in result ? (
        <RunResults run={result.run} onFocus={onFocus} />
      ) : (
        <AttemptResult attempt={result.attempt} onFocus={onFocus} />
      )}
    </div>
  );
}

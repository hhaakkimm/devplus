import type { components } from "@devplus/api-client";
import { Verdict } from "@/components/lab/run-results";
import { RunStatus } from "@/components/lab/run-status";
import {
  dateText,
  isActive,
  money,
  scoreText,
  statusText,
  verdictText,
} from "@/lib/runs";

type Run = components["schemas"]["RunOut"];

// The verdict and, per case, only the score and whether it passed: the cases are the task's secret.
// While the attempt is queued or running it shows the status, which refreshes the page at the end.
export function AttemptResult({ run }: { run: Run }) {
  if (isActive(run.status)) return <RunStatus id={run.id} run={run} />;
  const results = run.results ?? [];
  return (
    <div className="grid gap-2">
      <p className="text-2xl font-semibold">{verdictText(run)}</p>
      {run.passed != null && run.status !== "done" && (
        <p className="text-sm text-muted-foreground">{statusText(run)}</p>
      )}
      {run.error && <p className="text-sm text-destructive">{run.error}</p>}
      <p>
        Прошло кейсов: {results.filter((r) => r.passed).length} из{" "}
        {run.cases_total}
      </p>
      <ul>
        {results.map((r) => (
          <li key={r.position}>
            Кейс {r.position}: {scoreText(r.score)}{" "}
            <Verdict passed={r.passed} />
          </li>
        ))}
      </ul>
      <p className="text-sm text-muted-foreground">
        Стоимость: {money(run.cost_usd)}
      </p>
    </div>
  );
}

export function AttemptHistory({ attempts }: { attempts: Run[] }) {
  if (attempts.length === 0) {
    return <p className="mt-2 text-muted-foreground">Попыток пока нет.</p>;
  }
  return (
    <ul className="mt-2 divide-y">
      {attempts.map((a) => (
        <li key={a.id} className="py-2 text-sm">
          <span className="font-medium">{dateText(a.created_at)}</span>{" "}
          <span className="text-muted-foreground">
            · {verdictText(a)} · балл {scoreText(a.score_avg)} ·{" "}
            {money(a.cost_usd)}
          </span>
        </li>
      ))}
    </ul>
  );
}

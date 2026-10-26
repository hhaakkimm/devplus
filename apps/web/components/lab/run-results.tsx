import type { components } from "@devplus/api-client";
import { money, scoreText } from "@/lib/runs";

type Run = components["schemas"]["RunOut"];
type Result = components["schemas"]["ResultOut"];
type Grade = {
  type: string;
  score: number;
  passed: boolean;
  skipped: boolean;
  error: string | null;
  sections: { name: string; score: number; reason: string }[] | null;
  comment: string | null;
};

const text = "break-words whitespace-pre-wrap";

export function Verdict({ passed }: { passed: boolean }) {
  return passed ? (
    <span aria-label="прошёл">✓</span>
  ) : (
    <span aria-label="не прошёл">✗</span>
  );
}

export function RunSummary({ run }: { run: Run }) {
  const results = run.results ?? [];
  const passed = results.filter((r) => r.passed).length;
  const ms = (v: number | null | undefined) => (v == null ? "—" : `${v} мс`);
  const items: [string, string][] = [
    ["Средний балл", scoreText(run.score_avg)],
    ["Прошло кейсов", `${passed} из ${results.length}`],
    [
      "Стоимость",
      `${money(run.cost_usd)} (лимит ${money(run.cost_limit_usd, 2)})`,
    ],
    [
      "Задержка p50 / p95",
      `${ms(run.latency_p50_ms)} / ${ms(run.latency_p95_ms)}`,
    ],
  ];
  return (
    <dl className="mt-6 grid gap-x-8 gap-y-3 sm:grid-cols-2">
      {items.map(([name, value]) => (
        <div key={name}>
          <dt className="text-sm text-muted-foreground">{name}</dt>
          <dd className="text-lg font-medium">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

// The answer of one case with its marks: a cut-off answer and a case error are shown as text.
export function Answer({ result }: { result: Result }) {
  return (
    <>
      {result.output && (
        <div className={`max-h-48 overflow-auto ${text}`}>{result.output}</div>
      )}
      {result.truncated && (
        <p className="mt-1 text-xs text-muted-foreground">обрезан</p>
      )}
      {result.error && (
        <p className={`mt-1 text-destructive ${text}`}>
          Ошибка: {result.error}
        </p>
      )}
    </>
  );
}

function Grades({ grades }: { grades: Grade[] }) {
  return (
    <ul className="space-y-2">
      {grades.map((g, i) => (
        <li key={i}>
          <span className="font-mono">{g.type}</span>:{" "}
          {g.skipped ? (
            "пропущен (нет эталона)"
          ) : (
            <>
              {scoreText(g.score)} <Verdict passed={g.passed} />
            </>
          )}
          {g.error && <p className={`text-destructive ${text}`}>{g.error}</p>}
          {g.sections && (
            <ul className="ml-4 list-disc">
              {g.sections.map((s) => (
                <li key={s.name} className={text}>
                  {s.name}: {s.score}/5. {s.reason}
                </li>
              ))}
            </ul>
          )}
          {g.comment && <p className={text}>{g.comment}</p>}
        </li>
      ))}
    </ul>
  );
}

export function RunTable({ results }: { results: Result[] }) {
  return (
    <div className="mt-6 overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b">
            <th className="w-12 py-2 pr-2 font-medium">№</th>
            <th className="py-2 pr-2 font-medium">Вход</th>
            <th className="py-2 pr-2 font-medium">Ответ</th>
            <th className="py-2 pr-2 font-medium">Оценки</th>
            <th className="py-2 font-medium">Балл</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr key={r.position} className="border-b align-top">
              <td className="py-2 pr-2">{r.position}</td>
              <td className="py-2 pr-2">
                {Object.entries(r.input_vars ?? {}).map(([name, value]) => (
                  <div key={name} className={`max-h-24 overflow-auto ${text}`}>
                    <span className="font-medium">{name}</span>: {value}
                  </div>
                ))}
              </td>
              <td className="py-2 pr-2">
                <Answer result={r} />
              </td>
              <td className="py-2 pr-2">
                <Grades grades={(r.grades ?? []) as Grade[]} />
              </td>
              <td className="py-2 whitespace-nowrap">
                {scoreText(r.score)} <Verdict passed={r.passed} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

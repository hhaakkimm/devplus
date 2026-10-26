import Link from "next/link";
import { Answer, Verdict } from "@/components/lab/run-results";
import { loadRun } from "@/lib/evals";
import {
  alignByPosition,
  dateText,
  deltaText,
  money,
  scoreText,
  statusText,
} from "@/lib/runs";

export default async function ComparePage({
  searchParams,
}: PageProps<"/lab/compare">) {
  const { a, b } = await searchParams;
  const heading = (
    <h1 className="mt-2 text-3xl font-semibold">Сравнение прогонов</h1>
  );
  const back = (
    <Link href="/lab" className="text-sm hover:underline">
      ← К Лаборатории
    </Link>
  );
  if (typeof a !== "string" || typeof b !== "string") {
    return (
      <>
        {back}
        {heading}
        <p className="mt-4 text-muted-foreground">
          Выберите два прогона на странице промпта.
        </p>
      </>
    );
  }
  const [runA, runB] = await Promise.all([loadRun(a), loadRun(b)]);
  const runs = [
    { label: "A", run: runA },
    { label: "B", run: runB },
  ];
  const cases = alignByPosition(runA.results ?? [], runB.results ?? []);

  return (
    <>
      {back}
      {heading}
      <table className="mt-6 w-full text-left text-sm">
        <thead>
          <tr className="border-b">
            <td />
            {runs.map(({ label, run }) => (
              <th key={label} scope="col" className="py-2 pr-2 font-medium">
                <Link href={`/lab/runs/${run.id}`} className="hover:underline">
                  {label}
                </Link>
                <div className="font-normal text-muted-foreground">
                  {dateText(run.created_at)} · {statusText(run)}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr className="border-b">
            <th scope="row" className="py-2 pr-2 font-medium">
              Средний балл
            </th>
            {runs.map(({ label, run }) => (
              <td key={label} className="py-2 pr-2">
                {scoreText(run.score_avg)}
              </td>
            ))}
          </tr>
          <tr className="border-b">
            <th scope="row" className="py-2 pr-2 font-medium">
              Стоимость
            </th>
            {runs.map(({ label, run }) => (
              <td key={label} className="py-2 pr-2">
                {money(run.cost_usd)}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
      {cases.map(({ position, a: ra, b: rb }) => (
        <section key={position} className="mt-8">
          <h2 className="font-medium">Кейс {position}</h2>
          {Object.entries((ra ?? rb)?.input_vars ?? {}).map(([name, value]) => (
            <p
              key={name}
              className="max-h-24 overflow-auto text-sm break-words whitespace-pre-wrap"
            >
              <span className="font-medium">{name}</span>: {value}
            </p>
          ))}
          <table className="mt-2 w-full table-fixed text-left text-sm">
            <thead>
              <tr className="border-b">
                <td className="w-24" />
                <th scope="col" className="py-2 pr-2 font-medium">
                  A
                </th>
                <th scope="col" className="py-2 font-medium">
                  B
                </th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b align-top">
                <th scope="row" className="py-2 pr-2 font-medium">
                  Ответ
                </th>
                {[ra, rb].map((r, i) => (
                  <td key={i} className="py-2 pr-2">
                    {r ? <Answer result={r} /> : "—"}
                  </td>
                ))}
              </tr>
              <tr className="border-b">
                <th scope="row" className="py-2 pr-2 font-medium">
                  Балл
                </th>
                {[ra, rb].map((r, i) => (
                  <td key={i} className="py-2 pr-2">
                    {r ? (
                      <>
                        {scoreText(r.score)} <Verdict passed={r.passed} />
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                ))}
              </tr>
              <tr className="border-b">
                <th scope="row" className="py-2 pr-2 font-medium">
                  Δ балла
                </th>
                <td colSpan={2} className="py-2 font-medium">
                  {deltaText(ra?.score, rb?.score)}
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      ))}
    </>
  );
}

import type { components } from "@devplus/api-client";
import { money } from "@/lib/runs";

type Review = components["schemas"]["ReviewOut"];
type Texts = { system: string; user_template: string };

export const VARIABLES_CHANGED =
  "Переписанная версия использует другие переменные — на текущих датасетах она не запустится";

const SEVERITY = { high: "высокая", medium: "средняя", low: "низкая" };

const text = "break-words whitespace-pre-wrap";

function Prompt({ title, texts }: { title: string; texts: Texts | null }) {
  return (
    <div className="grid content-start gap-2">
      <h3 className="font-medium">{title}</h3>
      {texts === null ? (
        <p className="text-sm text-muted-foreground">Версия недоступна.</p>
      ) : (
        [
          ["Системный промпт", texts.system],
          ["Шаблон сообщения", texts.user_template],
        ].map(([label, value]) => (
          <div key={label}>
            <p className="text-sm text-muted-foreground">{label}</p>
            <pre className={`rounded-lg bg-muted p-3 text-sm ${text}`}>
              {value || "—"}
            </pre>
          </div>
        ))
      )}
    </div>
  );
}

// The critic's answer: the checklist, the issues and the rewrite beside the reviewed text.
// `original` is null when its version can no longer be read.
export function ReviewResult({
  review,
  original,
}: {
  review: Review;
  original: Texts | null;
}) {
  return (
    <>
      <section aria-labelledby="sections" className="mt-8">
        <h2 id="sections" className="text-xl font-semibold">
          Оценка по разделам
        </h2>
        <table className="mt-2 w-full text-left text-sm">
          <thead>
            <tr className="border-b">
              <th scope="col" className="py-2 pr-2 font-medium">
                Раздел
              </th>
              <th scope="col" className="py-2 pr-2 font-medium">
                Оценка
              </th>
              <th scope="col" className="py-2 font-medium">
                Комментарий
              </th>
            </tr>
          </thead>
          <tbody>
            {review.sections.map((s) => (
              <tr key={s.name} className="border-b align-top">
                <th scope="row" className="py-2 pr-2 font-medium">
                  {s.name}
                </th>
                <td className="py-2 pr-2 whitespace-nowrap">{s.score} из 5</td>
                <td className={`py-2 ${text}`}>{s.comment}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section aria-labelledby="issues" className="mt-8">
        <h2 id="issues" className="text-xl font-semibold">
          Проблемы
        </h2>
        {review.issues.length === 0 ? (
          <p className="mt-2 text-muted-foreground">Проблем не найдено.</p>
        ) : (
          <ul className="mt-2 divide-y">
            {review.issues.map((issue, i) => (
              <li key={i} className={`py-2 text-sm ${text}`}>
                <span className="font-medium">{SEVERITY[issue.severity]}</span>{" "}
                {issue.text}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section aria-labelledby="rewrite" className="mt-8">
        <h2 id="rewrite" className="text-xl font-semibold">
          Переписанная версия
        </h2>
        {review.variables_changed && (
          <p className="mt-2 rounded-lg border border-destructive/50 p-3 text-sm text-destructive">
            {VARIABLES_CHANGED}
          </p>
        )}
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <Prompt title="Исходная" texts={original} />
          <Prompt title="Переписанная" texts={review.rewritten} />
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          Стоимость разбора: {money(review.cost_usd)}
        </p>
      </section>
    </>
  );
}

import Link from "next/link";
import { loadQuizCatalog } from "@/lib/quizzes";
import { loadQuizResults } from "@/lib/session";

export default async function QuizzesPage() {
  const [catalog, results] = await Promise.all([
    loadQuizCatalog(),
    loadQuizResults(),
  ]);
  return (
    <>
      <h1 className="text-3xl font-semibold">Квизы</h1>
      <p className="mt-2 text-muted-foreground">
        Любой квиз можно пройти в любой момент, читать статью для этого не
        нужно. Лучший результат сохраняется.
      </p>
      {catalog.length === 0 && (
        <p className="mt-6 text-muted-foreground">Квизов пока нет.</p>
      )}
      {catalog.map((m) => (
        <section
          key={m.slug}
          aria-labelledby={`module-${m.slug}`}
          className="mt-8"
        >
          <h2 id={`module-${m.slug}`} className="text-xl font-semibold">
            {m.title}
          </h2>
          <ul className="mt-3 space-y-2">
            {m.quizzes.map((q) => {
              const best = results.get(q.slug);
              return (
                <li key={q.slug}>
                  <Link
                    href={`/quizzes/${q.slug}`}
                    className="font-medium hover:underline"
                  >
                    {best && best.best_score === best.total ? "✓ " : ""}
                    {q.title}
                  </Link>
                  <span className="ml-2 text-sm text-muted-foreground">
                    вопросов: {q.count}
                    {best &&
                      ` · лучший результат ${best.best_score} из ${best.total}`}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </>
  );
}

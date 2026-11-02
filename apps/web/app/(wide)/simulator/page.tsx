import Link from "next/link";
import { serverApi } from "@/lib/api";
import { loadCurriculum } from "@/lib/content";
import { unwrap } from "@/lib/evals";

export default async function SimulatorPage() {
  const [res, modules] = await Promise.all([
    (await serverApi()).GET("/api/simulator/tasks"),
    loadCurriculum(),
  ]);
  const tasks = unwrap(res, "GET /api/simulator/tasks");
  const titles = new Map(modules.map((m) => [m.slug, m.title]));
  const byModule = Map.groupBy(tasks, (t) => t.module);

  return (
    <>
      <h1 className="text-3xl font-semibold">Симулятор</h1>
      <p className="mt-2 text-muted-foreground">
        Собери схему системы, прогони её под нагрузкой и отправь на разбор.
      </p>
      {tasks.length === 0 && (
        <p className="mt-6 text-muted-foreground">Задач пока нет.</p>
      )}
      {[...byModule].map(([moduleSlug, list]) => (
        <section
          key={moduleSlug}
          aria-labelledby={`module-${moduleSlug}`}
          className="mt-8"
        >
          <h2 id={`module-${moduleSlug}`} className="text-xl font-semibold">
            {titles.get(moduleSlug) ?? moduleSlug}
          </h2>
          <ul className="mt-3 space-y-3">
            {list.map((t) => (
              <li key={t.slug}>
                <Link
                  href={`/simulator/${t.module}/${t.slug}`}
                  className="font-medium hover:underline"
                >
                  {t.title}
                </Link>
                {t.solved && (
                  <span className="ml-2 text-sm text-muted-foreground">
                    ✓ решено
                  </span>
                )}
                <p className="text-sm text-muted-foreground">{t.summary}</p>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </>
  );
}

import Link from "next/link";
import { loadCurriculum } from "@/lib/content";
import { loadTasks } from "@/lib/evals";

export default async function TrainerPage() {
  const [tasks, modules] = await Promise.all([loadTasks(), loadCurriculum()]);
  const titles = new Map(modules.map((m) => [m.slug, m.title]));
  const byModule = Map.groupBy(tasks, (t) => t.module);

  return (
    <>
      <h1 className="text-3xl font-semibold">Тренажёр</h1>
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
                  href={`/trainer/${t.module}/${t.slug}`}
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

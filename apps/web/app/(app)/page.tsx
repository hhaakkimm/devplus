import Link from "next/link";
import { loadCurriculum } from "@/lib/content";
import { moduleProgress } from "@/lib/progress";
import { loadDone } from "@/lib/session";

export default async function Home() {
  const [modules, done] = await Promise.all([loadCurriculum(), loadDone()]);
  return (
    <>
      <h1 className="text-3xl font-semibold">Программа</h1>
      {modules.map((m) => {
        const progress = moduleProgress(m, done);
        return (
          <section
            key={m.slug}
            aria-labelledby={`module-${m.slug}`}
            className="mt-8"
          >
            <div className="flex items-baseline justify-between">
              <h2 id={`module-${m.slug}`} className="text-xl font-semibold">
                {m.title}
              </h2>
              <span className="text-sm text-muted-foreground">
                {progress.done} из {progress.total}
              </span>
            </div>
            <p className="text-muted-foreground">{m.description}</p>
            <ul className="mt-3 space-y-1">
              {m.lessons.map((l) => (
                <li key={l.slug}>
                  <Link href={`/lessons/${l.slug}`} className="hover:underline">
                    {done.has(l.slug) ? "✓ " : ""}
                    {l.title}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </>
  );
}

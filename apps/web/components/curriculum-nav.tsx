import Link from "next/link";
import { groupLessons, type Module } from "@/lib/content";
import { moduleProgress } from "@/lib/progress";

// The whole programme as a tree: the current module is open, the rest are folded.
// `current` is "module/lesson". Plain <details>: no client JS needed to fold and unfold.
export function CurriculumNav({
  modules,
  done,
  current,
}: {
  modules: Module[];
  done: ReadonlySet<string>;
  current: string;
}) {
  const currentModule = current.split("/")[0];
  return (
    <nav aria-label="Программа" className="text-sm">
      {modules
        .filter((m) => m.lessons.length > 0)
        .map((m) => {
          const progress = moduleProgress(m, done);
          return (
            <details
              key={m.slug}
              open={m.slug === currentModule}
              className="border-b py-1 last:border-b-0"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-2 rounded-md px-2 py-1.5 font-medium hover:bg-muted [&::-webkit-details-marker]:hidden">
                <span>{m.title}</span>
                <span className="shrink-0 text-xs font-normal text-muted-foreground">
                  {progress.done}/{progress.total}
                </span>
              </summary>
              <div className="pb-1">
                {groupLessons(m).map((g) => (
                  <div key={g.title ?? "_"} className="mt-3 first:mt-1">
                    {g.title && (
                      <p className="mb-1 border-l-2 border-primary px-2 py-0.5 text-xs font-semibold tracking-wide text-foreground uppercase">
                        {g.title}
                      </p>
                    )}
                    <ul className="ml-1 border-l pl-1">
                      {g.lessons.map((l) => {
                        const active = l.slug === current;
                        return (
                          <li key={l.slug}>
                            <Link
                              href={`/lessons/${l.slug}`}
                              aria-current={active ? "page" : undefined}
                              className={`block rounded-md px-2 py-1 ${
                                active
                                  ? "bg-secondary font-medium text-secondary-foreground"
                                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
                              }`}
                            >
                              {done.has(l.slug) ? "✓ " : ""}
                              {l.title}
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
              </div>
            </details>
          );
        })}
    </nav>
  );
}

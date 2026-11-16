import Link from "next/link";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { groupLessons, loadCurriculum } from "@/lib/content";
import { moduleProgress } from "@/lib/progress";
import { loadDone } from "@/lib/session";

export default async function Home() {
  const [modules, done] = await Promise.all([loadCurriculum(), loadDone()]);
  const shown = modules.filter((m) => m.lessons.length > 0);
  return (
    <>
      <h1 className="text-3xl font-semibold">Программа</h1>
      {/* Modules without lessons (system design, AI so far) hold only tasks of other sections. */}
      {/* Long modules (imported articles) start collapsed so the page stays scannable. */}
      <Accordion
        multiple
        defaultValue={shown
          .filter((m) => m.lessons.length <= 10)
          .map((m) => m.slug)}
        className="mt-6 gap-3"
      >
        {shown.map((m) => {
          const progress = moduleProgress(m, done);
          return (
            <AccordionItem
              key={m.slug}
              value={m.slug}
              role="region"
              aria-label={m.title}
              className="rounded-xl border bg-card px-4 shadow-xs"
            >
              <AccordionTrigger className="items-center py-4 hover:no-underline">
                <span className="flex-1">
                  <span className="block text-lg font-semibold">{m.title}</span>
                  <span className="block text-sm font-normal text-muted-foreground">
                    {m.description}
                  </span>
                </span>
                <Badge
                  variant="secondary"
                  className={
                    progress.done === progress.total
                      ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
                      : undefined
                  }
                >
                  {progress.done === progress.total ? "✓ " : ""}
                  {progress.done} из {progress.total}
                </Badge>
              </AccordionTrigger>
              <AccordionContent className="[&_a]:no-underline">
                {/* Subsections come from `sections` in _module.json; a flat module is one untitled group. */}
                <div className="space-y-3 pb-2">
                  {groupLessons(m).map((g) => (
                    <section
                      key={g.title ?? "_"}
                      className="overflow-hidden rounded-lg border bg-muted/30"
                    >
                      {g.title && (
                        <h3 className="flex items-center justify-between gap-3 border-b border-l-4 border-l-primary bg-muted/60 px-3 py-2 text-sm font-semibold">
                          <span>{g.title}</span>
                          <span className="text-xs font-normal text-muted-foreground">
                            {g.lessons.filter((l) => done.has(l.slug)).length}{" "}
                            из {g.lessons.length}
                          </span>
                        </h3>
                      )}
                      <ul className="p-1">
                        {g.lessons.map((l) => (
                          <li key={l.slug}>
                            <Link
                              href={`/lessons/${l.slug}`}
                              className={`block rounded-md px-2 py-1.5 text-sm hover:bg-muted ${
                                done.has(l.slug)
                                  ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                                  : ""
                              }`}
                            >
                              {done.has(l.slug) ? "✓ " : ""}
                              {l.title}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </section>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </>
  );
}

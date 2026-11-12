import Link from "next/link";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { loadCurriculum } from "@/lib/content";
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
              className="rounded-lg border px-4"
            >
              <AccordionTrigger className="items-center py-4 hover:no-underline">
                <span className="flex-1">
                  <span className="block text-lg font-semibold">{m.title}</span>
                  <span className="block text-sm font-normal text-muted-foreground">
                    {m.description}
                  </span>
                </span>
                <Badge variant="secondary">
                  {progress.done} из {progress.total}
                </Badge>
              </AccordionTrigger>
              <AccordionContent>
                <ul className="space-y-1.5 pb-2">
                  {m.lessons.map((l) => (
                    <li key={l.slug}>
                      <Link
                        href={`/lessons/${l.slug}`}
                        className="text-sm hover:underline"
                      >
                        {done.has(l.slug) ? "✓ " : ""}
                        {l.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </>
  );
}

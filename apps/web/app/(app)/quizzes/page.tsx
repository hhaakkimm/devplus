import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
      <div className="mt-6 space-y-4">
        {catalog.map((m) => (
          <Card key={m.slug} role="region" aria-label={m.title}>
            <CardHeader>
              <CardTitle className="text-lg">{m.title}</CardTitle>
              <CardDescription>Квизов: {m.quizzes.length}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="divide-y">
                {m.quizzes.map((q) => {
                  const best = results.get(q.slug);
                  return (
                    <li key={q.slug}>
                      <Link
                        href={`/quizzes/${q.slug}`}
                        className="flex items-center justify-between gap-3 py-2 hover:underline"
                      >
                        <span className="font-medium">{q.title}</span>
                        <span className="flex items-center gap-2 text-sm text-muted-foreground">
                          вопросов: {q.count}
                          {best && (
                            <Badge
                              variant={
                                best.best_score === best.total
                                  ? "default"
                                  : "secondary"
                              }
                            >
                              лучший результат {best.best_score} из {best.total}
                            </Badge>
                          )}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}

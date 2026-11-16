import { notFound } from "next/navigation";
import { LangToggle } from "@/components/lang-toggle";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { QuizRunner } from "@/components/quiz";
import { loadQuiz } from "@/lib/quizzes";
import { loadQuizAttempts, loadQuizResults } from "@/lib/session";

export default async function QuizPage({
  params,
  searchParams,
}: PageProps<"/quizzes/[module]/[quiz]">) {
  const { module: moduleSlug, quiz: quizSlug } = await params;
  const { lang } = await searchParams;
  const en = lang === "en";
  // Fetch results alongside the quiz: an anonymous visitor must be redirected, not shown a 404.
  const [quiz, results, attempts] = await Promise.all([
    loadQuiz(moduleSlug, quizSlug, undefined, en ? "en" : undefined),
    loadQuizResults(),
    loadQuizAttempts(moduleSlug, quizSlug),
  ]);
  if (!quiz) notFound();
  const best = results.get(quiz.slug);
  return (
    <article>
      <div className="flex items-start justify-between gap-3">
        <h1 className="text-3xl font-semibold">{quiz.title}</h1>
        {quiz.hasEn && <LangToggle path={`/quizzes/${quiz.slug}`} en={en} />}
      </div>
      <p className="mt-2 text-sm text-muted-foreground">
        Вопросов: {quiz.questions.length}
        {quiz.source && (
          <>
            {" · "}
            <a
              href={quiz.source}
              target="_blank"
              rel="noreferrer noopener"
              className="underline"
            >
              оригинал на Hello Interview
            </a>
            {!(en && quiz.hasEn) && " (перевод)"}
          </>
        )}
      </p>
      {best && (
        <Card className="mt-4" role="region" aria-label="Твои результаты">
          <CardContent className="flex flex-wrap gap-x-10 gap-y-3 text-sm">
            <div>
              <p className="text-muted-foreground">Лучший результат</p>
              <p className="text-lg font-semibold">
                {best.best_score} из {best.total}
              </p>
            </div>
            {/* Results from before the history existed have a best score but no attempts. */}
            {attempts.length > 0 && (
              <div>
                <p className="text-muted-foreground">Последние попытки</p>
                <ul className="flex flex-wrap gap-2">
                  {attempts.map((a) => (
                    <li key={a.created_at}>
                      <Badge
                        variant={a.score === a.total ? "default" : "secondary"}
                      >
                        {a.score} из {a.total} ·{" "}
                        {new Date(a.created_at).toLocaleDateString("ru-RU", {
                          day: "numeric",
                          month: "short",
                        })}
                      </Badge>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
      <div className="mt-6" lang={en && quiz.hasEn ? "en" : undefined}>
        <QuizRunner quiz={quiz} />
      </div>
    </article>
  );
}

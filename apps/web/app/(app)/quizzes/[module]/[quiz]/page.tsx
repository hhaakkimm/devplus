import { notFound } from "next/navigation";
import { LangToggle } from "@/components/lang-toggle";
import { QuizRunner } from "@/components/quiz";
import { loadQuiz } from "@/lib/quizzes";
import { loadQuizResults } from "@/lib/session";

export default async function QuizPage({
  params,
  searchParams,
}: PageProps<"/quizzes/[module]/[quiz]">) {
  const { module: moduleSlug, quiz: quizSlug } = await params;
  const { lang } = await searchParams;
  const en = lang === "en";
  // Fetch results alongside the quiz: an anonymous visitor must be redirected, not shown a 404.
  const [quiz, results] = await Promise.all([
    loadQuiz(moduleSlug, quizSlug, undefined, en ? "en" : undefined),
    loadQuizResults(),
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
        {best && ` · лучший результат ${best.best_score} из ${best.total}`}
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
      <div className="mt-6" lang={en && quiz.hasEn ? "en" : undefined}>
        <QuizRunner quiz={quiz} />
      </div>
    </article>
  );
}

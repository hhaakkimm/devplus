import { MDXRemote } from "next-mdx-remote/rsc";
import Link from "next/link";
import { notFound } from "next/navigation";
import remarkGfm from "remark-gfm";
import { ProgressToggle } from "@/components/progress-toggle";
import { loadLesson } from "@/lib/content";
import { loadQuiz } from "@/lib/quizzes";
import { loadDone, loadQuizResults } from "@/lib/session";

export default async function LessonPage({
  params,
}: PageProps<"/lessons/[module]/[lesson]">) {
  const { module: moduleSlug, lesson: lessonSlug } = await params;
  // Fetch progress alongside the lesson: an anonymous visitor must be redirected, not shown a 404.
  const [lesson, done, results] = await Promise.all([
    loadLesson(moduleSlug, lessonSlug),
    loadDone(),
    loadQuizResults(),
  ]);
  if (!lesson) notFound();
  const quiz = lesson.quiz ? await loadQuiz(moduleSlug, lesson.quiz) : null;
  const best = quiz ? results.get(quiz.slug) : undefined;
  return (
    <article>
      <h1 className="text-3xl font-semibold">{lesson.title}</h1>
      <div className="prose dark:prose-invert mt-6 max-w-none">
        <MDXRemote
          source={lesson.source}
          options={{ mdxOptions: { remarkPlugins: [remarkGfm] } }}
        />
      </div>
      {quiz && (
        <aside className="mt-8 rounded border p-4">
          <p className="font-medium">Проверь себя</p>
          <Link href={`/quizzes/${quiz.slug}`} className="hover:underline">
            {quiz.title}: вопросов {quiz.questions.length}
          </Link>
          {best && (
            <span className="text-muted-foreground">
              {" "}
              · лучший результат {best.best_score} из {best.total}
            </span>
          )}
        </aside>
      )}
      <div className="mt-8 flex items-center gap-4">
        <ProgressToggle slug={lesson.slug} done={done.has(lesson.slug)} />
        <Link href="/" className="hover:underline">
          ← К программе
        </Link>
      </div>
    </article>
  );
}

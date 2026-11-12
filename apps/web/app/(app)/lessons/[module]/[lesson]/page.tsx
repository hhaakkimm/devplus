import { MDXRemote } from "next-mdx-remote/rsc";
import Link from "next/link";
import { notFound } from "next/navigation";
import remarkGfm from "remark-gfm";
import { ProgressToggle } from "@/components/progress-toggle";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
          components={{
            table: Table,
            thead: TableHeader,
            tbody: TableBody,
            tr: TableRow,
            th: TableHead,
            td: TableCell,
          }}
        />
      </div>
      {quiz && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Проверь себя</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-3">
            <Link
              href={`/quizzes/${quiz.slug}`}
              className="font-medium hover:underline"
            >
              {quiz.title}: вопросов {quiz.questions.length}
            </Link>
            {best && (
              <Badge variant="secondary">
                лучший результат {best.best_score} из {best.total}
              </Badge>
            )}
          </CardContent>
        </Card>
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

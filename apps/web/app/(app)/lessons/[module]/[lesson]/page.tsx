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
import { loadCurriculum, loadLesson } from "@/lib/content";
import { loadQuiz } from "@/lib/quizzes";
import { loadDone, loadQuizResults } from "@/lib/session";

// `not-prose`: the shadcn table has its own spacing, prose styles would double it.
function MdxTable(props: React.ComponentProps<"table">) {
  return (
    <div className="not-prose my-6 rounded-lg border bg-card px-2">
      <Table {...props} />
    </div>
  );
}

export default async function LessonPage({
  params,
}: PageProps<"/lessons/[module]/[lesson]">) {
  const { module: moduleSlug, lesson: lessonSlug } = await params;
  // Fetch progress alongside the lesson: an anonymous visitor must be redirected, not shown a 404.
  const [lesson, done, results, modules] = await Promise.all([
    loadLesson(moduleSlug, lessonSlug),
    loadDone(),
    loadQuizResults(),
    loadCurriculum(),
  ]);
  if (!lesson) notFound();
  const mod = modules.find((m) => m.slug === moduleSlug);
  const at = mod ? mod.lessons.findIndex((l) => l.slug === lesson.slug) : -1;
  const prev = mod && at > 0 ? mod.lessons[at - 1] : undefined;
  const next = mod && at >= 0 ? mod.lessons[at + 1] : undefined;
  const quiz = lesson.quiz ? await loadQuiz(moduleSlug, lesson.quiz) : null;
  const best = quiz ? results.get(quiz.slug) : undefined;
  return (
    <article>
      {mod && <p className="text-sm text-muted-foreground">{mod.title}</p>}
      <h1 className="mt-1 text-3xl font-semibold tracking-tight">
        {lesson.title}
      </h1>
      <div className="prose prose-neutral dark:prose-invert mt-8 max-w-none prose-headings:scroll-mt-20 prose-headings:tracking-tight prose-a:font-medium prose-a:text-primary prose-a:no-underline hover:prose-a:underline prose-img:mx-auto prose-img:rounded-lg prose-img:border prose-img:bg-white prose-img:p-2 prose-hr:my-10">
        <MDXRemote
          source={lesson.source}
          options={{ mdxOptions: { remarkPlugins: [remarkGfm] } }}
          components={{
            table: MdxTable,
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
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:underline"
        >
          ← К программе
        </Link>
      </div>
      {(prev || next) && (
        <nav
          aria-label="Соседние уроки"
          className="mt-8 grid gap-3 border-t pt-6 sm:grid-cols-2"
        >
          {prev ? (
            <Link
              href={`/lessons/${prev.slug}`}
              className="rounded-lg border bg-card p-3 text-sm transition-colors hover:bg-muted"
            >
              <span className="block text-xs text-muted-foreground">
                ← Предыдущий
              </span>
              {prev.title}
            </Link>
          ) : (
            <span />
          )}
          {next && (
            <Link
              href={`/lessons/${next.slug}`}
              className="rounded-lg border bg-card p-3 text-right text-sm transition-colors hover:bg-muted sm:col-start-2"
            >
              <span className="block text-xs text-muted-foreground">
                Следующий →
              </span>
              {next.title}
            </Link>
          )}
        </nav>
      )}
    </article>
  );
}

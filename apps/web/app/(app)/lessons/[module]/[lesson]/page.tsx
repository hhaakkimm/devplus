import { compileMDX } from "next-mdx-remote/rsc";
import Link from "next/link";
import { notFound } from "next/navigation";
import remarkGfm from "remark-gfm";
import { LangToggle } from "@/components/lang-toggle";
import { LessonToc } from "@/components/lesson-toc";
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
import { headingIds, type TocItem } from "@/lib/toc";

// `not-prose`: the shadcn table has its own spacing, prose styles would double it.
// Tables stay sans and 1rem: the serif article size is too big for dense cells.
function MdxTable(props: React.ComponentProps<"table">) {
  return (
    <div className="not-prose my-6 rounded-lg border bg-card px-2 font-sans text-base">
      <Table {...props} />
    </div>
  );
}

export default async function LessonPage({
  params,
  searchParams,
}: PageProps<"/lessons/[module]/[lesson]">) {
  const { module: moduleSlug, lesson: lessonSlug } = await params;
  const { lang } = await searchParams;
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
  const en = lang === "en" && !!lesson.en;
  const quiz = lesson.quiz ? await loadQuiz(moduleSlug, lesson.quiz) : null;
  const best = quiz ? results.get(quiz.slug) : undefined;
  // Compiled here (not in <MDXRemote>) so the plugin has filled `toc` before the page renders.
  const toc: TocItem[] = [];
  const { content } = await compileMDX({
    source: en ? lesson.en!.source : lesson.source,
    options: { mdxOptions: { remarkPlugins: [remarkGfm, headingIds(toc)] } },
    components: {
      table: MdxTable,
      thead: TableHeader,
      tbody: TableBody,
      tr: TableRow,
      th: TableHead,
      td: TableCell,
    },
  });
  return (
    <article className="mx-auto max-w-[42.5rem]">
      <div className="flex items-center justify-between gap-3">
        {mod ? (
          <p className="text-sm text-muted-foreground">{mod.title}</p>
        ) : (
          <span />
        )}
        {lesson.en && <LangToggle path={`/lessons/${lesson.slug}`} en={en} />}
      </div>
      <h1 className="mt-1 text-3xl font-semibold tracking-tight sm:text-4xl">
        {en ? lesson.en!.title : lesson.title}
      </h1>
      <div id="lesson-article" className="relative">
        <LessonToc articleId="lesson-article" items={toc} />
        <div
          lang={en ? "en" : undefined}
          className="article prose prose-neutral dark:prose-invert mt-8 max-w-none font-serif prose-headings:font-sans prose-headings:scroll-mt-20 prose-headings:tracking-tight prose-a:font-normal prose-a:text-primary prose-a:underline prose-a:decoration-primary/40 prose-a:underline-offset-4 hover:prose-a:decoration-primary prose-blockquote:border-l-2 prose-blockquote:border-primary/40 prose-blockquote:font-normal prose-blockquote:text-muted-foreground prose-img:mx-auto prose-img:rounded-lg prose-img:border prose-img:bg-white prose-img:p-2 prose-hr:my-10"
        >
          {content}
        </div>
      </div>
      {quiz && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Проверь себя</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-3">
            <Link
              href={`/quizzes/${quiz.slug}${en && quiz.hasEn ? "?lang=en" : ""}`}
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

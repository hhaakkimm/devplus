import { MDXRemote } from "next-mdx-remote/rsc";
import Link from "next/link";
import {
  GradingNotice,
  RetryButton,
} from "@/components/code-review/attempt-actions";
import { ResultView } from "@/components/code-review/result-view";
import { ReviewWorkspace } from "@/components/code-review/review-workspace";
import {
  createReviewAttempt,
  highlightFile,
  loadReviewAttempts,
  loadReviewTask,
} from "@/lib/code-review";

export default async function ReviewTaskPage({
  params,
}: PageProps<"/code-review/[module]/[slug]">) {
  const { module: moduleSlug, slug } = await params;
  const task = await loadReviewTask(moduleSlug, slug);
  // newest first; a new draft is made only when the task has no attempt at all
  const key = `${moduleSlug}/${slug}`;
  const attempts = (await loadReviewAttempts()).filter(
    (a) => a.task_key === key,
  );
  const attempt = attempts[0] ?? (await createReviewAttempt(moduleSlug, slug));
  const highlighted =
    attempt.status === "draft" || attempt.status === "failed"
      ? await Promise.all(
          Object.entries(task.files).map(([path, source]) =>
            highlightFile(path, source),
          ),
        )
      : [];

  return (
    <>
      <Link href="/code-review" className="text-sm hover:underline">
        ← К задачам
      </Link>
      <h1 className="mt-2 text-3xl font-semibold">{task.title}</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {task.difficulty} · около {task.estimate_min} мин
      </p>
      <details open className="mt-6">
        <summary className="cursor-pointer text-xl font-semibold">
          Условие
        </summary>
        <div className="prose dark:prose-invert mt-3 max-w-none">
          <MDXRemote source={task.statement} />
        </div>
      </details>
      <div className="mt-8">
        {attempt.status === "grading" && <GradingNotice />}
        {attempt.status === "graded" && (
          <div className="grid gap-6">
            <ResultView attempt={attempt} />
            <RetryButton module={moduleSlug} slug={slug} />
          </div>
        )}
        {highlighted.length > 0 && (
          <ReviewWorkspace
            key={attempt.id}
            task={task}
            highlighted={highlighted}
            attempt={attempt}
          />
        )}
      </div>
    </>
  );
}

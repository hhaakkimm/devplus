import { MDXRemote } from "next-mdx-remote/rsc";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AttemptForm } from "@/components/trainer/attempt-form";
import { AttemptHistory, AttemptResult } from "@/components/trainer/attempts";
import { loadAttempts, loadRun, loadTasks } from "@/lib/evals";
import { isActive } from "@/lib/runs";
import { loadTaskStatement } from "@/lib/tasks";

export default async function TaskPage({
  params,
}: PageProps<"/trainer/[module]/[task]">) {
  const { module: moduleSlug, task: taskSlug } = await params;
  const [tasks, statement, attempts] = await Promise.all([
    loadTasks(),
    loadTaskStatement(moduleSlug, taskSlug),
    loadAttempts(moduleSlug, taskSlug),
  ]);
  const task = tasks.find(
    (t) => t.module === moduleSlug && t.slug === taskSlug,
  );
  if (!task || statement === null) notFound();
  // The list has no per-case verdicts: read them for the newest attempt once it has settled.
  const latest = attempts[0];
  const result =
    latest && !isActive(latest.status) ? await loadRun(latest.id) : latest;

  return (
    <>
      <Link href="/trainer" className="text-sm hover:underline">
        ← К тренажёру
      </Link>
      <h1 className="mt-2 text-3xl font-semibold">{task.title}</h1>
      {task.solved && (
        <p className="mt-1 text-sm text-muted-foreground">✓ решено</p>
      )}
      <div className="prose dark:prose-invert mt-6 max-w-none">
        <MDXRemote source={statement} />
      </div>
      <section aria-labelledby="solution" className="mt-8">
        <h2 id="solution" className="mb-4 text-xl font-semibold">
          Решение
        </h2>
        <AttemptForm
          module={moduleSlug}
          task={taskSlug}
          model={task.model}
          effort={task.effort}
        />
      </section>
      {result && (
        <section aria-labelledby="result" className="mt-8">
          <h2 id="result" className="mb-2 text-xl font-semibold">
            Результат
          </h2>
          <AttemptResult run={result} />
        </section>
      )}
      <section aria-labelledby="history" className="mt-8">
        <h2 id="history" className="text-xl font-semibold">
          История попыток
        </h2>
        <AttemptHistory attempts={attempts} />
      </section>
    </>
  );
}

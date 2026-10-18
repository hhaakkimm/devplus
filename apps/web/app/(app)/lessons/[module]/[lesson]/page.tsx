import { MDXRemote } from "next-mdx-remote/rsc";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ProgressToggle } from "@/components/progress-toggle";
import { loadLesson } from "@/lib/content";
import { loadDone } from "@/lib/session";

export default async function LessonPage({
  params,
}: PageProps<"/lessons/[module]/[lesson]">) {
  const { module: moduleSlug, lesson: lessonSlug } = await params;
  // Fetch progress alongside the lesson: an anonymous visitor must be redirected, not shown a 404.
  const [lesson, done] = await Promise.all([
    loadLesson(moduleSlug, lessonSlug),
    loadDone(),
  ]);
  if (!lesson) notFound();
  return (
    <article>
      <h1 className="text-3xl font-semibold">{lesson.title}</h1>
      <div className="prose dark:prose-invert mt-6 max-w-none">
        <MDXRemote source={lesson.source} />
      </div>
      <div className="mt-8 flex items-center gap-4">
        <ProgressToggle slug={lesson.slug} done={done.has(lesson.slug)} />
        <Link href="/" className="hover:underline">
          ← К программе
        </Link>
      </div>
    </article>
  );
}

import { MDXRemote } from "next-mdx-remote/rsc";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Workspace } from "@/components/simulator/workspace";
import { serverApi } from "@/lib/api";
import { CONTENT_DIR, loadLesson } from "@/lib/content";
import { unwrap } from "@/lib/evals";

const num = (n: number) => n.toLocaleString("ru-RU");
const pct = (share: number) => `${num(+(share * 100).toFixed(2))}%`;

export default async function SimulatorTaskPage({
  params,
}: PageProps<"/simulator/[module]/[task]">) {
  const { module: moduleSlug, task: taskSlug } = await params;
  const api = await serverApi();
  const [taskRes, catalogRes, lesson] = await Promise.all([
    api.GET("/api/simulator/tasks/{module}/{task}", {
      params: { path: { module: moduleSlug, task: taskSlug } },
    }),
    api.GET("/api/simulator/components"),
    loadLesson(moduleSlug, taskSlug, CONTENT_DIR, "simulator"),
  ]);
  const task = unwrap(taskRes, "GET /api/simulator/tasks/{module}/{task}");
  const catalog = unwrap(catalogRes, "GET /api/simulator/components");
  if (!lesson) notFound();
  const labels = new Map(catalog.map((c) => [c.type, c.label]));

  const statement = (
    <div className="grid gap-6">
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <MDXRemote source={lesson.source} />
      </div>
      <section aria-labelledby="sim-scale-h">
        <h2 id="sim-scale-h" className="text-lg font-semibold">
          Масштаб
        </h2>
        <p className="mt-1 text-sm">
          Пик {num(task.scale.peak_rps)} rps, из них чтений{" "}
          {pct(task.scale.read_ratio)}.
        </p>
      </section>
      <section aria-labelledby="sim-scenarios-h">
        <h2 id="sim-scenarios-h" className="text-lg font-semibold">
          Открытые сценарии
        </h2>
        <ul className="mt-2 grid gap-3 text-sm">
          {task.scenarios.map((s) => (
            <li key={s.id}>
              <p className="font-medium">{s.title}</p>
              <p className="text-muted-foreground">
                Нагрузка ×{num(s.multiplier)} в течение {num(s.duration_s)} с
                {s.failure &&
                  `, отказ: ${labels.get(s.failure.type) ?? s.failure.type} (${s.failure.mode === "node" ? "узел целиком" : "одна копия"})`}
              </p>
              <p>
                Цели: средняя задержка до {num(s.max_latency_ms)} мс, ошибок до{" "}
                {pct(s.max_error_rate)},{" "}
                {s.max_message_loss > 0
                  ? `потерь сообщений до ${pct(s.max_message_loss)}`
                  : "без потерь сообщений"}
                .
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );

  return (
    <>
      <Link href="/simulator" className="text-sm hover:underline">
        ← К задачам
      </Link>
      <h1 className="mt-2 mb-6 text-3xl font-semibold">{task.title}</h1>
      <Workspace
        module={moduleSlug}
        slug={taskSlug}
        catalog={catalog}
        statement={statement}
      />
    </>
  );
}

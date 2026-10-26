import Link from "next/link";
import { RunStatus } from "@/components/lab/run-status";
import { RunSummary, RunTable } from "@/components/lab/run-results";
import { loadRun } from "@/lib/evals";

export default async function RunPage({ params }: PageProps<"/lab/runs/[id]">) {
  const { id } = await params;
  const run = await loadRun(id);

  return (
    <>
      <Link href="/lab" className="text-sm hover:underline">
        ← К Лаборатории
      </Link>
      <h1 className="mt-2 text-3xl font-semibold">Прогон</h1>
      <div className="mt-2">
        <RunStatus id={id} run={run} />
      </div>
      <RunSummary run={run} />
      {(run.results ?? []).length > 0 && <RunTable results={run.results!} />}
    </>
  );
}

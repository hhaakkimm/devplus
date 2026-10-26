"use client";

import { useRouter } from "next/navigation";
import { RunDialog, type RunBody } from "@/components/lab/run-dialog";
import { browserApi } from "@/lib/browser-api";

// Runs the latest version of the prompt.
// shortcut: no version picker, a run of an older version is not possible; add a select when needed
export function RunLauncher({
  versionId,
  versionNumber,
  datasets,
}: {
  versionId: string;
  versionNumber: number;
  datasets: { id: string; name: string; case_count: number }[];
}) {
  const router = useRouter();
  const request = (b: RunBody) => ({ ...b, prompt_version_id: versionId });
  return (
    <RunDialog<{ id: string }>
      label="Запустить прогон"
      submitLabel="Запустить"
      note={`Версия ${versionNumber}`}
      datasets={datasets}
      estimate={(b) =>
        browserApi.POST("/api/evals/runs/estimate", { body: request(b) })
      }
      submit={(b) => browserApi.POST("/api/evals/runs", { body: request(b) })}
      onDone={(created) => router.push(`/lab/runs/${created.id}`)}
    />
  );
}

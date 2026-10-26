"use client";

import { useRouter } from "next/navigation";
import { RunDialog, type RunBody } from "@/components/lab/run-dialog";
import { browserApi } from "@/lib/browser-api";

type Check = { run_a: { id: string }; run_b: { id: string } };

// Runs the reviewed and the rewritten version on a dataset, then opens their comparison.
export function CheckDialog({
  reviewId,
  datasets,
  disabled,
}: {
  reviewId: string;
  datasets: { id: string; name: string; case_count: number }[];
  disabled: boolean;
}) {
  const router = useRouter();
  return (
    <RunDialog<Check>
      label="Проверить улучшение"
      submitLabel="Проверить"
      note="Исходная и переписанная версии пройдут по одному датасету."
      datasets={datasets}
      disabled={disabled}
      submit={(b: RunBody) =>
        browserApi.POST("/api/review/{review_id}/check", {
          params: { path: { review_id: reviewId } },
          body: b,
        })
      }
      onDone={(r) =>
        router.push(`/lab/compare?a=${r.run_a.id}&b=${r.run_b.id}`)
      }
    />
  );
}

"use client";

import type { components } from "@devplus/api-client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { browserApi } from "@/lib/browser-api";
import { isActive, statusText } from "@/lib/runs";

type Run = components["schemas"]["RunOut"];
type Progress = Pick<Run, "status" | "cases_done" | "cases_total" | "error">;

const POLL_MS = 2000;

// Shows the status and, while the run is queued or running, asks the API every 2 s;
// when it settles the server part of the page is refreshed with the results.
export function RunStatus({ id, run }: { id: string; run: Progress }) {
  const router = useRouter();
  const [polled, setPolled] = useState<Progress | null>(null);
  const shown = isActive(run.status) && polled ? polled : run;

  useEffect(() => {
    if (!isActive(run.status)) return;
    let stopped = false;
    (async () => {
      while (!stopped) {
        await new Promise((resolve) => setTimeout(resolve, POLL_MS));
        if (stopped) return;
        try {
          const { data } = await browserApi.GET("/api/evals/runs/{run_id}", {
            params: { path: { run_id: id } },
          });
          if (stopped) return;
          if (data) setPolled(data);
          // no data: the session ended or the run is gone, the server page deals with it
          if (!data || !isActive(data.status)) {
            router.refresh();
            return;
          }
        } catch {
          // a dropped request: try again on the next tick
        }
      }
    })();
    return () => {
      stopped = true;
    };
  }, [id, run.status, router]);

  return (
    <div role="status" className="text-lg font-medium">
      {statusText(shown)}
      {shown.error && (
        <p className="mt-1 text-sm font-normal text-destructive">
          {shown.error}
        </p>
      )}
    </div>
  );
}

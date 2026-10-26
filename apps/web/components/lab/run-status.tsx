"use client";

import type { components } from "@devplus/api-client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { browserApi, SIGN_IN_URL } from "@/lib/browser-api";
import { isActive, pollRun, statusText } from "@/lib/runs";

type Run = components["schemas"]["RunOut"];
type Progress = Pick<Run, "status" | "cases_done" | "cases_total" | "error">;

// Shows the status and, while the run is queued or running, asks the API every 2 s;
// when it settles the server part of the page is refreshed with the results.
export function RunStatus({ id, run }: { id: string; run: Progress }) {
  const router = useRouter();
  const [polled, setPolled] = useState<Progress | null>(null);
  const shown = isActive(run.status) && polled ? polled : run;

  useEffect(() => {
    if (!isActive(run.status)) return;
    const stop = new AbortController();
    pollRun(
      () =>
        browserApi.GET("/api/evals/runs/{run_id}", {
          params: { path: { run_id: id } },
        }),
      setPolled,
      stop.signal,
    ).then((end) => {
      if (end === "sign-in") window.location.assign(SIGN_IN_URL);
      else if (end === "refresh") router.refresh();
    });
    return () => stop.abort();
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

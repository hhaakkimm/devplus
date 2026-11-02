"use client";

import { useEffect } from "react";
import { ErrorList } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { browserApi } from "@/lib/browser-api";

const REFRESH_MS = 5000;

// The grading runs in the request that sent it; a page opened meanwhile (or after a reload) waits here.
// shortcut: refreshes forever, even if the grader died; the API lets a stale `grading` attempt be sent again
export function GradingNotice() {
  const { router } = useAction();
  useEffect(() => {
    const id = setInterval(() => router.refresh(), REFRESH_MS);
    return () => clearInterval(id);
  }, [router]);
  return (
    <p role="status" className="rounded-lg border p-4">
      Идёт оценка… Страница обновится сама.
    </p>
  );
}

// A new draft for the same task; the page then shows the empty workspace.
export function RetryButton({
  module: moduleSlug,
  slug,
}: {
  module: string;
  slug: string;
}) {
  const { busy, error, run } = useAction();
  return (
    <div className="grid gap-2">
      <ErrorList messages={error ? [error] : []} />
      <div>
        <Button
          type="button"
          disabled={busy}
          onClick={() =>
            run(() =>
              browserApi.POST(
                "/api/code-review/tasks/{module}/{slug}/attempts",
                { params: { path: { module: moduleSlug, slug } } },
              ),
            )
          }
        >
          Попробовать снова
        </Button>
      </div>
    </div>
  );
}

"use client";

import { ErrorList } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { browserApi } from "@/lib/browser-api";

// Sharing is for the author, copying for anyone who can see the item.
export function ItemActions({
  kind,
  id,
  shared,
  mine,
}: {
  kind: "prompts" | "datasets";
  id: string;
  shared: boolean;
  mine: boolean;
}) {
  const { busy, error, run, router } = useAction();

  const toggleShared = () =>
    run<{ id: string }>(() =>
      kind === "prompts"
        ? browserApi.PATCH("/api/evals/prompts/{prompt_id}", {
            params: { path: { prompt_id: id } },
            body: { shared: !shared },
          })
        : browserApi.PATCH("/api/evals/datasets/{dataset_id}", {
            params: { path: { dataset_id: id } },
            body: { shared: !shared },
          }),
    );

  const copy = () =>
    run<{ id: string }>(
      () =>
        kind === "prompts"
          ? browserApi.POST("/api/evals/prompts/{prompt_id}/copy", {
              params: { path: { prompt_id: id } },
            })
          : browserApi.POST("/api/evals/datasets/{dataset_id}/copy", {
              params: { path: { dataset_id: id } },
            }),
      (created) => router.push(`/lab/${kind}/${created.id}`),
    );

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap gap-2">
        {mine && (
          <Button variant="outline" onClick={toggleShared} disabled={busy}>
            {shared ? "Сделать личным" : "Поделиться с командой"}
          </Button>
        )}
        <Button variant="outline" onClick={copy} disabled={busy}>
          Скопировать себе
        </Button>
      </div>
      <ErrorList messages={error ? [error] : []} />
    </div>
  );
}

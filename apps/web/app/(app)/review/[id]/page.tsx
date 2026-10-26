import Link from "next/link";
import { CheckDialog } from "@/components/review/check-dialog";
import { ReviewResult } from "@/components/review/review-result";
import { loadDatasets, loadReview, loadVersion } from "@/lib/evals";

export default async function ReviewResultPage({
  params,
}: PageProps<"/review/[id]">) {
  const { id } = await params;
  const [review, datasets] = await Promise.all([
    loadReview(id),
    loadDatasets(),
  ]);
  const original = await loadVersion(
    review.prompt_id,
    review.prompt_version_id,
  );

  return (
    <>
      <Link href="/review" className="text-sm hover:underline">
        ← Новое ревью
      </Link>
      <h1 className="mt-2 text-3xl font-semibold">Ревью промпта</h1>
      <ReviewResult review={review} original={original} />
      <div className="mt-6 flex flex-wrap items-center gap-4">
        <CheckDialog
          reviewId={id}
          datasets={datasets}
          disabled={review.variables_changed || datasets.length === 0}
        />
        {datasets.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Для проверки нужен датасет: создай его в{" "}
            <Link href="/lab/datasets/new" className="underline">
              Лаборатории
            </Link>
            .
          </p>
        )}
      </div>
    </>
  );
}

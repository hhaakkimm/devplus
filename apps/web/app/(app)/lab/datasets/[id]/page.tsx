import Link from "next/link";
import { AddCaseForm } from "@/components/lab/add-case-form";
import { ImportJsonl } from "@/components/lab/import-jsonl";
import { ItemActions } from "@/components/lab/item-actions";
import { buttonVariants } from "@/components/ui/button";
import { loadDataset } from "@/lib/evals";
import { requireUser } from "@/lib/session";
import { cn } from "@/lib/utils";

export default async function DatasetPage({
  params,
}: PageProps<"/lab/datasets/[id]">) {
  const { id } = await params;
  const [user, dataset] = await Promise.all([requireUser(), loadDataset(id)]);
  const mine = dataset.owner_login === user.login;
  const exportLink = (
    <a
      href={`/api/evals/datasets/${id}/export`}
      download={`${dataset.name}.jsonl`}
      className={cn(buttonVariants({ variant: "outline" }))}
    >
      Экспорт JSONL
    </a>
  );

  return (
    <>
      <Link href="/lab?tab=datasets" className="text-sm hover:underline">
        ← К Лаборатории
      </Link>
      <h1 className="mt-2 text-3xl font-semibold">{dataset.name}</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {mine
          ? dataset.shared
            ? "Доступен команде"
            : "Личный"
          : `автор: ${dataset.owner_login}`}
      </p>
      <div className="mt-4">
        <ItemActions
          kind="datasets"
          id={id}
          shared={dataset.shared}
          mine={mine}
        />
      </div>
      <div className="mt-6">
        {mine ? (
          <ImportJsonl datasetId={id} hasCases={dataset.cases.length > 0}>
            {exportLink}
          </ImportJsonl>
        ) : (
          exportLink
        )}
      </div>
      {dataset.cases.length === 0 ? (
        <p className="mt-6 text-muted-foreground">Кейсов пока нет.</p>
      ) : (
        <table className="mt-6 w-full text-left text-sm">
          <thead>
            <tr className="border-b">
              <th className="w-12 py-2 pr-2 font-medium">№</th>
              <th className="py-2 pr-2 font-medium">Переменные</th>
              <th className="py-2 font-medium">Эталон</th>
            </tr>
          </thead>
          <tbody>
            {/* Positions in the table are 1..n as the API's messages count them, not stored positions. */}
            {dataset.cases.map((c, i) => (
              <tr key={c.id} className="border-b align-top">
                <td className="py-2 pr-2">{i + 1}</td>
                <td className="py-2 pr-2">
                  {Object.entries(c.variables).map(([name, value]) => (
                    <div
                      key={name}
                      className="max-h-24 overflow-auto break-words whitespace-pre-wrap"
                    >
                      <span className="font-medium">{name}</span>: {value}
                    </div>
                  ))}
                </td>
                <td className="py-2 break-words whitespace-pre-wrap">
                  {c.expected}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {mine && (
        <section aria-labelledby="add-case" className="mt-8">
          <h2 id="add-case" className="mb-4 text-xl font-semibold">
            Новый кейс
          </h2>
          <AddCaseForm datasetId={id} />
        </section>
      )}
    </>
  );
}

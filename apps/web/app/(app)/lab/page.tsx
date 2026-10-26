import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { loadDatasets, loadPrompts } from "@/lib/evals";
import { requireUser } from "@/lib/session";
import { cn } from "@/lib/utils";

function Tab({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "-mb-px border-b-2 px-1 pb-2",
        active
          ? "border-foreground font-medium"
          : "border-transparent text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </Link>
  );
}

export default async function LabPage({ searchParams }: PageProps<"/lab">) {
  const { tab } = await searchParams;
  const datasets = tab === "datasets";
  const [user, rows] = await Promise.all([
    requireUser(),
    datasets
      ? loadDatasets().then((list) =>
          list.map((d) => ({ ...d, meta: `кейсов: ${d.case_count}` })),
        )
      : loadPrompts().then((list) =>
          list.map((p) => ({ ...p, meta: `версия ${p.latest_version}` })),
        ),
  ]);
  const base = datasets ? "/lab/datasets" : "/lab/prompts";

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold">Лаборатория</h1>
        <div className="flex gap-2">
          <Link href="/lab/prompts/new" className={buttonVariants()}>
            Новый промпт
          </Link>
          <Link
            href="/lab/datasets/new"
            className={cn(buttonVariants({ variant: "outline" }))}
          >
            Новый датасет
          </Link>
        </div>
      </div>
      <nav
        aria-label="Разделы Лаборатории"
        className="mt-6 flex gap-4 border-b"
      >
        <Tab href="/lab" active={!datasets}>
          Промпты
        </Tab>
        <Tab href="/lab?tab=datasets" active={datasets}>
          Датасеты
        </Tab>
      </nav>
      {rows.length === 0 ? (
        <p className="mt-6 text-muted-foreground">
          {datasets ? "Датасетов пока нет." : "Промптов пока нет."}
        </p>
      ) : (
        <ul className="mt-4 divide-y">
          {rows.map((r) => (
            <li
              key={r.id}
              className="flex items-baseline justify-between gap-4 py-3"
            >
              <Link
                href={`${base}/${r.id}`}
                className="font-medium hover:underline"
              >
                {r.name}
              </Link>
              <span className="text-sm text-muted-foreground">
                {r.owner_login !== user.login && `автор: ${r.owner_login} · `}
                {r.meta}
                {r.owner_login === user.login && r.shared && " · общий"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

import Link from "next/link";
import { selectClass } from "@/components/lab/form-parts";
import { ItemActions } from "@/components/lab/item-actions";
import { PromptForm } from "@/components/lab/prompt-form";
import { RunLauncher } from "@/components/lab/run-launcher";
import { Button } from "@/components/ui/button";
import { loadDatasets, loadPrompt, loadRuns } from "@/lib/evals";
import { dateText, money, scoreText, statusText } from "@/lib/runs";
import { requireUser } from "@/lib/session";

export default async function PromptPage({
  params,
}: PageProps<"/lab/prompts/[id]">) {
  const { id } = await params;
  const [user, prompt, datasets, runs] = await Promise.all([
    requireUser(),
    loadPrompt(id),
    loadDatasets(),
    loadRuns(id),
  ]);
  const mine = prompt.owner_login === user.login;
  const versions = [...prompt.versions].reverse();
  const versionNumber = new Map(prompt.versions.map((v) => [v.id, v.number]));

  return (
    <>
      <Link href="/lab" className="text-sm hover:underline">
        ← К Лаборатории
      </Link>
      <h1 className="mt-2 text-3xl font-semibold">{prompt.name}</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {mine
          ? prompt.shared
            ? "Доступен команде"
            : "Личный"
          : `автор: ${prompt.owner_login}`}
      </p>
      <div className="mt-4">
        <ItemActions
          kind="prompts"
          id={id}
          shared={prompt.shared}
          mine={mine}
        />
      </div>
      <div className="mt-2">
        <RunLauncher
          versionId={versions[0].id}
          versionNumber={versions[0].number}
          datasets={datasets}
        />
      </div>
      <section aria-labelledby="runs" className="mt-8">
        <h2 id="runs" className="text-xl font-semibold">
          Прогоны
        </h2>
        {runs.length === 0 ? (
          <p className="mt-2 text-muted-foreground">Прогонов пока нет.</p>
        ) : (
          <ul className="mt-2 divide-y">
            {runs.map((r) => (
              <li key={r.id} className="py-2 text-sm">
                <Link
                  href={`/lab/runs/${r.id}`}
                  className="font-medium hover:underline"
                >
                  {dateText(r.created_at)}
                </Link>{" "}
                <span className="text-muted-foreground">
                  · версия {versionNumber.get(r.prompt_version_id)} ·{" "}
                  {statusText(r)} · балл {scoreText(r.score_avg)} ·{" "}
                  {money(r.cost_usd)}
                </span>
              </li>
            ))}
          </ul>
        )}
        {runs.length >= 2 && (
          <form
            action="/lab/compare"
            className="mt-4 flex flex-wrap items-end gap-3"
          >
            {(["a", "b"] as const).map((name, i) => (
              <label key={name} className="grid gap-1.5 text-sm font-medium">
                Прогон {name.toUpperCase()}
                <select
                  name={name}
                  defaultValue={runs[1 - i].id}
                  className={selectClass}
                >
                  {runs.map((r) => (
                    <option key={r.id} value={r.id}>
                      {dateText(r.created_at)} · {statusText(r)}
                    </option>
                  ))}
                </select>
              </label>
            ))}
            <Button type="submit" variant="outline">
              Сравнить
            </Button>
          </form>
        )}
      </section>
      {mine && (
        <section aria-labelledby="new-version" className="mt-8">
          <h2 id="new-version" className="mb-4 text-xl font-semibold">
            Новая версия
          </h2>
          <PromptForm promptId={id} initial={versions[0]} />
        </section>
      )}
      <section aria-labelledby="versions" className="mt-8">
        <h2 id="versions" className="text-xl font-semibold">
          Версии
        </h2>
        {versions.map((v) => (
          <article key={v.id} className="mt-4 grid gap-2">
            <h3 className="font-medium">Версия {v.number}</h3>
            <p className="text-sm text-muted-foreground">
              {v.model} · effort {v.effort} · макс. токенов {v.max_tokens}
            </p>
            {v.system && (
              <pre className="whitespace-pre-wrap break-words rounded-lg bg-muted p-3 text-sm">
                {v.system}
              </pre>
            )}
            <pre className="whitespace-pre-wrap break-words rounded-lg bg-muted p-3 text-sm">
              {v.user_template}
            </pre>
          </article>
        ))}
      </section>
    </>
  );
}

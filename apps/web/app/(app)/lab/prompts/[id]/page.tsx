import Link from "next/link";
import { ItemActions } from "@/components/lab/item-actions";
import { PromptForm } from "@/components/lab/prompt-form";
import { loadPrompt } from "@/lib/evals";
import { requireUser } from "@/lib/session";

export default async function PromptPage({
  params,
}: PageProps<"/lab/prompts/[id]">) {
  const { id } = await params;
  const [user, prompt] = await Promise.all([requireUser(), loadPrompt(id)]);
  const mine = prompt.owner_login === user.login;
  const versions = [...prompt.versions].reverse();

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

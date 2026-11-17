"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiDetail, browserApi } from "@/lib/browser-api";

type Pending = {
  telegram: { id: number; first_name: string; username: string | null };
  login: string;
};

export function LinkConfirm() {
  const router = useRouter();
  const [pending, setPending] = useState<Pending | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [spent, setSpent] = useState(false);

  // One fetch only: the Telegram id shown here is the one confirm sends back for the server to check.
  useEffect(() => {
    let live = true;
    browserApi
      .GET("/api/auth/telegram/link/pending")
      .then(({ data, error, response }) => {
        if (!live) return;
        if (data) setPending(data);
        else setError(apiDetail(error, response.status));
      })
      .catch(() => live && setError("Нет связи с сервером"));
    return () => {
      live = false;
    };
  }, []);

  async function confirm() {
    if (!pending) return;
    setBusy(true);
    setError(null);
    try {
      const { error, response } = await browserApi.POST(
        "/api/auth/telegram/link/confirm",
        { body: { telegram_id: pending.telegram.id } },
      );
      if (response.ok) {
        router.push("/tg/linked");
        return;
      }
      setError(apiDetail(error, response.status));
      if (response.status === 400) setSpent(true);
    } catch {
      setError("Нет связи с сервером");
    } finally {
      setBusy(false);
    }
  }

  const who = pending && (
    <strong>
      {pending.telegram.first_name} (
      {pending.telegram.username ? `@${pending.telegram.username}, ` : ""}id{" "}
      {pending.telegram.id})
    </strong>
  );

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-start justify-center gap-4 px-4">
      {pending && (
        <>
          <h1 className="text-3xl font-semibold">
            Привязать Telegram {who} к аккаунту <strong>{pending.login}</strong>
            ?
          </h1>
          <p className="text-muted-foreground">
            Подтверждение даст этому Telegram доступ к аккаунту. Если ты не
            запрашивал привязку, закрой страницу.
          </p>
          <Button onClick={confirm} disabled={busy || spent}>
            Привязать
          </Button>
        </>
      )}
      {!pending && !error && <p className="text-muted-foreground">Загрузка…</p>}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
          {(spent || !pending) && " Начни привязку заново из Telegram."}
        </p>
      )}
    </main>
  );
}

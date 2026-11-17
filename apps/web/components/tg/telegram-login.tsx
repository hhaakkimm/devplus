"use client";

import Script from "next/script";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import { apiDetail, browserApi } from "@/lib/browser-api";
import { clearMiniApp, markMiniApp } from "@/lib/miniapp";
import { nextStep } from "@/lib/telegram";

type View = "loading" | "outside" | "link" | "error";

function Outside() {
  return (
    <>
      <h1 className="text-3xl font-semibold">Открой приложение из Telegram</h1>
      {/* A plain <a>: this is an API route, not a page to client-navigate to. */}
      <a href="/api/auth/github/login" className={buttonVariants()}>
        Обычный вход
      </a>
    </>
  );
}

export function TelegramLogin() {
  const [view, setView] = useState<View>("loading");
  const [error, setError] = useState<string | null>(null);
  const [linking, setLinking] = useState(false);
  const initData = useRef("");
  const inFlight = useRef(false);

  // The load, the retry on return to the app and the "Я вошёл" button all come here.
  const attempt = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const { response } = await browserApi.POST("/api/auth/telegram", {
        body: { init_data: initData.current },
      });
      const step = nextStep(response.status);
      // Hard navigation on purpose: the pages after sign-in must not come from the client router cache.
      /* eslint-disable @next/next/no-location-assign-relative-destination */
      if (step === "home") window.location.assign("/");
      else if (step === "no-access") window.location.assign("/no-access");
      /* eslint-enable @next/next/no-location-assign-relative-destination */
      else if (step === "open-telegram") setView("outside");
      else if (step === "link") setView("link");
      else {
        setError(`Не удалось войти (${response.status})`);
        setView("error");
      }
    } catch {
      setError("Нет связи с сервером");
      setView("error");
    } finally {
      inFlight.current = false;
    }
  }, []);

  function start() {
    const tg = window.Telegram?.WebApp;
    if (!tg?.initData) {
      clearMiniApp();
      setView("outside");
      return;
    }
    markMiniApp();
    tg.ready();
    tg.expand();
    initData.current = tg.initData;
    void attempt();
  }

  // After "Войти через GitHub" the user comes back to the WebView: retry the sign-in.
  useEffect(() => {
    if (view !== "link") return;
    const tg = window.Telegram?.WebApp;
    const onVisible = () => {
      if (document.visibilityState === "visible") void attempt();
    };
    const onActivated = () => void attempt();
    document.addEventListener("visibilitychange", onVisible);
    tg?.onEvent("activated", onActivated);
    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      tg?.offEvent("activated", onActivated);
    };
  }, [view, attempt]);

  async function linkStart() {
    setLinking(true);
    setError(null);
    try {
      const { data, error, response } = await browserApi.POST(
        "/api/auth/telegram/link-start",
        { body: { init_data: initData.current } },
      );
      if (data) window.Telegram?.WebApp.openLink(data.url);
      else setError(apiDetail(error, response.status));
    } catch {
      setError("Нет связи с сервером");
    } finally {
      setLinking(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-start justify-center gap-4 px-4">
      {/* Without this script initData is empty. A load error is the same as being outside Telegram. */}
      <Script
        src="https://telegram.org/js/telegram-web-app.js"
        strategy="afterInteractive"
        onReady={start}
        onError={() => {
          clearMiniApp();
          setView("outside");
        }}
      />
      {view === "loading" && <p className="text-muted-foreground">Входим…</p>}
      {view === "outside" && <Outside />}
      {view === "link" && (
        <>
          <h1 className="text-3xl font-semibold">Привяжи GitHub</h1>
          <p className="text-muted-foreground">
            Этот Telegram ещё не привязан к аккаунту devplus. Войди через
            GitHub, потом вернись сюда.
          </p>
          <Button onClick={linkStart} disabled={linking}>
            Войти через GitHub
          </Button>
          <Button variant="outline" onClick={() => void attempt()}>
            Я вошёл, продолжить
          </Button>
        </>
      )}
      {view === "error" && (
        <>
          <h1 className="text-3xl font-semibold">Не удалось войти</h1>
          <Button onClick={() => void attempt()}>Повторить</Button>
        </>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </main>
  );
}

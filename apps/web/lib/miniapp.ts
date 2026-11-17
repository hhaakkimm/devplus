export const MINIAPP_COOKIE = "miniapp";

// Inside the Telegram WebView a 401 goes to /tg (sign in by Telegram), not to the GitHub login.
// Takes a Cookie header or `document.cookie`, so one function serves server and client.
export function signInUrl(cookieHeader: string): string {
  const inMiniApp = cookieHeader
    .split(";")
    .some((c) => c.trim() === `${MINIAPP_COOKIE}=1`);
  return inMiniApp ? "/tg" : "/api/auth/github/login";
}

export function markMiniApp(): void {
  // shortcut: Telegram Web (фрейм) не поддерживаем, SameSite=lax cookie там может не сохраниться; менять, если команда пользуется Telegram Web
  document.cookie = `${MINIAPP_COOKIE}=1; path=/; max-age=2592000; SameSite=Lax`;
}

export function clearMiniApp(): void {
  document.cookie = `${MINIAPP_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

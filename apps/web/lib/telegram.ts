// The slice of the Telegram WebApp API we use (telegram-web-app.js defines it on window).
declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        initData: string;
        ready(): void;
        expand(): void;
        openLink(url: string): void;
        onEvent(event: "activated", cb: () => void): void;
        offEvent(event: "activated", cb: () => void): void;
      };
    };
  }
}

export type Step = "home" | "link" | "no-access" | "open-telegram" | "error";

// What POST /api/auth/telegram answered, as the next thing the page does.
export function nextStep(status: number): Step {
  if (status === 200) return "home";
  if (status === 404) return "link";
  if (status === 403) return "no-access";
  if (status === 401) return "open-telegram";
  return "error";
}

export function linkFailedMessage(reason: string | undefined): string {
  if (reason === "invalid") return "Ссылка устарела или уже использована.";
  if (reason === "not_allowed")
    return "Твоего GitHub-логина нет в списке доступа.";
  return "Не удалось привязать Telegram.";
}

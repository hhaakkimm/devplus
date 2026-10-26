import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { apiDetail, SIGN_IN_URL } from "@/lib/browser-api";

type Result<T> = { data?: T; error?: unknown; response: Response };

// One request at a time per component: `busy` covers the request and the refresh or navigation
// after it, so a button that sends a request is disabled until the new page state is in place.
export function useAction() {
  const router = useRouter();
  const [sending, setSending] = useState(false);
  const [routing, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  async function run<T>(
    request: () => Promise<Result<T>>,
    onDone: (data: T) => void = () => router.refresh(),
  ) {
    setSending(true);
    setError(null);
    try {
      const { data, error, response } = await request();
      if (response.ok) startTransition(() => onDone(data as T));
      else if (response.status === 401) window.location.assign(SIGN_IN_URL);
      else setError(apiDetail(error, response.status));
    } catch {
      setError("Нет связи с сервером");
    } finally {
      setSending(false);
    }
  }

  return { busy: sending || routing, error, setError, run, router };
}

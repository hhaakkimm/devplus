"use client";

import { Button } from "@/components/ui/button";

export default function Error({
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-start justify-center gap-4 px-4">
      <h1 className="text-3xl font-semibold">Что-то пошло не так</h1>
      <Button onClick={() => retry()}>Попробовать снова</Button>
    </main>
  );
}

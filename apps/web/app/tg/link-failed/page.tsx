import { linkFailedMessage } from "@/lib/telegram";

export default async function TelegramLinkFailedPage({
  searchParams,
}: PageProps<"/tg/link-failed">) {
  const { reason } = await searchParams;
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-start justify-center gap-4 px-4">
      <h1 className="text-3xl font-semibold">Привязка не удалась</h1>
      <p className="text-muted-foreground">
        {linkFailedMessage(typeof reason === "string" ? reason : undefined)}
      </p>
    </main>
  );
}

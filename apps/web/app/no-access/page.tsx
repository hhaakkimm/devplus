import { buttonVariants } from "@/components/ui/button";

export default async function NoAccess({
  searchParams,
}: PageProps<"/no-access">) {
  const { signed_out } = await searchParams;
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-start justify-center gap-4 px-4">
      {signed_out ? (
        <h1 className="text-3xl font-semibold">Ты вышел из devplus</h1>
      ) : (
        <>
          <h1 className="text-3xl font-semibold">Нет доступа</h1>
          <p className="text-muted-foreground">
            Попроси добавить твой GitHub-логин в список доступа devplus.
          </p>
        </>
      )}
      {/* A plain <a>: this is an API route, not a page to client-navigate to. */}
      <a href="/api/auth/github/login" className={buttonVariants()}>
        Войти через GitHub
      </a>
    </main>
  );
}

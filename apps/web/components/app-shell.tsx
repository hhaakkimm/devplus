import { Header } from "@/components/header";
import { requireUser } from "@/lib/session";

// The signed-in page frame; `wide` is for pages that need room, like code next to its comments.
export async function AppShell({
  children,
  wide = false,
}: {
  children: React.ReactNode;
  wide?: boolean;
}) {
  const user = await requireUser();
  return (
    <>
      <Header user={user} />
      <main
        className={`mx-auto w-full ${wide ? "max-w-7xl" : "max-w-3xl"} flex-1 px-4 py-8`}
      >
        {children}
      </main>
    </>
  );
}

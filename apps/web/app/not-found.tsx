import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-start justify-center gap-4 px-4">
      <h1 className="text-3xl font-semibold">Страница не найдена</h1>
      <Link href="/" className="hover:underline">
        ← К программе
      </Link>
    </main>
  );
}

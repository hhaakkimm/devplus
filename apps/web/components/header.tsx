import type { components } from "@devplus/api-client";
import Image from "next/image";
import Link from "next/link";
import { LogoutButton } from "@/components/logout-button";

const NAV = [
  { href: "/", label: "Программа" },
  { href: "/lab", label: "Лаборатория" },
  { href: "/review", label: "Ревью" },
  { href: "/trainer", label: "Тренажёр" },
  { href: "/code-review", label: "Code Review" },
  { href: "/simulator", label: "Симулятор" },
];

export function Header({ user }: { user: components["schemas"]["MeOut"] }) {
  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-y-2 px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <Link href="/" className="font-semibold">
            devplus
          </Link>
          <nav aria-label="Разделы" className="flex gap-4 text-sm">
            {NAV.map((l) => (
              <Link key={l.href} href={l.href} className="hover:underline">
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-2">
          {user.avatar_url && (
            <Image
              src={user.avatar_url}
              alt={user.login}
              width={32}
              height={32}
              className="rounded-full"
            />
          )}
          <LogoutButton />
        </div>
      </div>
    </header>
  );
}

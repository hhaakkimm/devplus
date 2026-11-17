import type { components } from "@devplus/api-client";
import Image from "next/image";
import Link from "next/link";
import { LogoutButton } from "@/components/logout-button";
import { NavLinks } from "@/components/nav-links";

const NAV = [
  { href: "/", label: "Программа" },
  { href: "/lab", label: "Лаборатория" },
  { href: "/review", label: "Ревью" },
  { href: "/trainer", label: "Тренажёр" },
  { href: "/code-review", label: "Code Review" },
  { href: "/simulator", label: "Симулятор" },
  { href: "/quizzes", label: "Квизы" },
];

export function Header({
  user,
  showLogout,
}: {
  user: components["schemas"]["MeOut"];
  showLogout: boolean;
}) {
  return (
    <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-1 px-4 py-2 md:flex-nowrap md:py-3">
        <Link href="/" className="font-semibold">
          devplus
        </Link>
        <div className="ml-auto flex items-center gap-2 md:order-last">
          {user.avatar_url && (
            <Image
              src={user.avatar_url}
              alt={user.login}
              width={32}
              height={32}
              className="rounded-full"
            />
          )}
          {showLogout && <LogoutButton />}
        </div>
        <NavLinks items={NAV} />
      </div>
    </header>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Item = { href: string; label: string };

// "/" is the curriculum: it also owns the lesson pages.
function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/" || pathname.startsWith("/lessons");
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function NavLinks({ items }: { items: Item[] }) {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Разделы"
      className="-mx-1 flex w-full gap-1 overflow-x-auto px-1 pb-1 text-sm [scrollbar-width:none] md:mx-0 md:w-auto md:pb-0"
    >
      {items.map((l) => {
        const active = isActive(pathname, l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={`shrink-0 rounded-md px-2.5 py-1.5 transition-colors ${
              active
                ? "bg-secondary font-medium text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}

import Link from "next/link";
import { cn } from "@/lib/utils";

// RU is the page without a query, EN is `?lang=en`. Rendered only where both versions exist.
export function LangToggle({ path, en }: { path: string; en: boolean }) {
  const item = (active: boolean) =>
    cn(
      "px-2.5 py-1 transition-colors",
      active
        ? "bg-primary text-primary-foreground"
        : "text-muted-foreground hover:bg-muted",
    );
  return (
    <nav
      aria-label="Язык материала"
      className="inline-flex shrink-0 overflow-hidden rounded-md border text-xs font-medium"
    >
      <Link
        href={path}
        scroll={false}
        hrefLang="ru"
        aria-current={en ? undefined : "true"}
        className={item(!en)}
      >
        RU
      </Link>
      <Link
        href={`${path}?lang=en`}
        scroll={false}
        hrefLang="en"
        aria-current={en ? "true" : undefined}
        className={item(en)}
      >
        EN
      </Link>
    </nav>
  );
}

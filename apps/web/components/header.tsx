import type { components } from "@devplus/api-client";
import Image from "next/image";
import Link from "next/link";
import { LogoutButton } from "@/components/logout-button";

export function Header({ user }: { user: components["schemas"]["MeOut"] }) {
  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
        <Link href="/" className="font-semibold">
          devplus
        </Link>
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

"use client";

import { Button } from "@/components/ui/button";
import { browserApi } from "@/lib/browser-api";

export function LogoutButton() {
  async function logout() {
    const { response } = await browserApi.POST("/api/auth/logout");
    // Do not claim "signed out" while the session is still alive.
    if (!response.ok) throw new Error(`Logout failed: ${response.status}`);
    // Hard navigation on purpose: drop the client router cache of the signed-in pages.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/no-access?signed_out=1");
  }

  return (
    <Button variant="ghost" onClick={logout}>
      Выйти
    </Button>
  );
}

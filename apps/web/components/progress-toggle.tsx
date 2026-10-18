"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { browserApi } from "@/lib/browser-api";

export function ProgressToggle({
  slug,
  done,
}: {
  slug: string;
  done: boolean;
}) {
  const router = useRouter();

  async function toggle() {
    const [module, lesson] = slug.split("/");
    const init = { params: { path: { module, lesson } } };
    const path = "/api/progress/{module}/{lesson}";
    await (done ? browserApi.DELETE(path, init) : browserApi.PUT(path, init));
    // Re-render from the server either way, so the button always shows the stored state.
    router.refresh();
  }

  return (
    <Button onClick={toggle} variant={done ? "outline" : "default"}>
      {done ? "Снять отметку" : "Отметить пройденным"}
    </Button>
  );
}

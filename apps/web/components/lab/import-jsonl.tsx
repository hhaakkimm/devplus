"use client";

import { useRef, useState } from "react";
import { ErrorList } from "@/components/lab/form-parts";
import { useAction } from "@/components/lab/use-action";
import { Button } from "@/components/ui/button";
import { browserApi } from "@/lib/browser-api";
import { parseJsonl } from "@/lib/jsonl";

const MAX_BYTES = 5 * 1024 * 1024;

type Preview = { text: string; count: number; errors: string[] };

// Reads the file, shows what the API will see, and replaces the dataset's cases on confirm.
export function ImportJsonl({
  datasetId,
  hasCases,
  children,
}: {
  datasetId: string;
  hasCases: boolean;
  children?: React.ReactNode; // more buttons for the row under the import button
}) {
  const input = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const { busy, error, setError, run, router } = useAction();

  async function choose(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // choosing the same file again must fire onChange
    if (!file) return;
    setError(null);
    const fail = (message: string) =>
      setPreview({ text: "", count: 0, errors: [message] });
    if (file.size > MAX_BYTES) return fail("Файл больше 5 МБ");
    let text: string;
    try {
      text = new TextDecoder("utf-8", { fatal: true }).decode(
        await file.arrayBuffer(),
      );
    } catch {
      return fail("Файл не в кодировке UTF-8");
    }
    const { cases, errors } = parseJsonl(text);
    setPreview({ text, count: cases.length, errors });
  }

  const upload = (text: string) =>
    run(
      () =>
        browserApi.PUT("/api/evals/datasets/{dataset_id}/cases", {
          params: { path: { dataset_id: datasetId } },
          body: text,
          bodySerializer: (body) => body, // raw JSONL, not JSON
          headers: { "Content-Type": "application/x-ndjson" },
        }),
      () => {
        setPreview(null);
        router.refresh();
      },
    );

  // The API reports bad lines as "Строка N: ...; Строка M: ..."
  const errors = preview?.errors.length
    ? preview.errors
    : (error?.split("; ") ?? []);

  return (
    <div className="grid gap-3">
      <input
        ref={input}
        type="file"
        hidden
        aria-label="Файл JSONL"
        onChange={choose}
      />
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          onClick={() => input.current?.click()}
          disabled={busy}
        >
          Импорт JSONL
        </Button>
        {children}
      </div>
      {preview && !preview.errors.length && (
        <div className="grid gap-2 rounded-lg border p-3 text-sm">
          <p>
            В файле кейсов: {preview.count}.
            {hasCases && " Они заменят все текущие кейсы датасета."}
          </p>
          <div className="flex gap-2">
            <Button onClick={() => upload(preview.text)} disabled={busy}>
              Загрузить кейсы
            </Button>
            <Button
              variant="ghost"
              onClick={() => setPreview(null)}
              disabled={busy}
            >
              Отмена
            </Button>
          </div>
        </div>
      )}
      {errors.length > 0 && (
        <div className="grid gap-1 text-sm">
          {preview?.errors.length ? (
            <p>В файле есть ошибки, ничего не загружено:</p>
          ) : null}
          <ErrorList messages={errors} />
        </div>
      )}
    </div>
  );
}

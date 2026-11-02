"use client";

import { useState } from "react";
import { ErrorList } from "@/components/lab/form-parts";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MAX_COMMENT_CHARS } from "@/lib/code-review-state";

// The form for the selected lines; `onAdd` returns an error text or null when the comment was taken.
export function CommentForm({
  file,
  range,
  onAdd,
  onCancel,
}: {
  file: string;
  range: [number, number];
  onAdd: (text: string) => string | null;
  onCancel: () => void;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const where = `${file}:${range[0] === range[1] ? range[0] : `${range[0]}–${range[1]}`}`;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(onAdd(text));
  }

  return (
    <form onSubmit={submit} className="mt-3 grid gap-2 rounded-lg border p-3">
      <label htmlFor="comment-text" className="text-sm font-medium">
        Замечание к <span className="font-mono">{where}</span>
        <span className="ml-2 font-normal text-muted-foreground">
          Shift+клик — диапазон
        </span>
      </label>
      <Textarea
        id="comment-text"
        autoFocus
        rows={3}
        maxLength={MAX_COMMENT_CHARS}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <ErrorList messages={error ? [error] : []} />
      <div className="flex gap-2">
        <Button type="submit">Добавить замечание</Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Отмена
        </Button>
      </div>
    </form>
  );
}

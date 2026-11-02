"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MAX_COMMENT_CHARS, type DraftComment } from "@/lib/code-review-state";

function Item({
  comment,
  onEdit,
  onRemove,
}: {
  comment: DraftComment;
  onEdit?: (text: string) => void;
  onRemove?: () => void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const { file, line_start: a, line_end: b } = comment;
  return (
    <li className="rounded-lg border p-2 text-sm">
      <p className="font-mono text-xs text-muted-foreground">
        {file}:{a === b ? a : `${a}–${b}`}
      </p>
      {draft === null ? (
        <p className="mt-1 break-words whitespace-pre-wrap">{comment.text}</p>
      ) : (
        <Textarea
          aria-label="Текст замечания"
          autoFocus
          rows={3}
          maxLength={MAX_COMMENT_CHARS}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="mt-1"
        />
      )}
      {onEdit && onRemove && (
        <div className="mt-2 flex gap-1">
          {draft === null ? (
            <Button
              type="button"
              size="xs"
              variant="outline"
              onClick={() => setDraft(comment.text)}
            >
              Изменить
            </Button>
          ) : (
            <Button
              type="button"
              size="xs"
              disabled={!draft.trim()}
              onClick={() => {
                onEdit(draft);
                setDraft(null);
              }}
            >
              Готово
            </Button>
          )}
          <Button type="button" size="xs" variant="ghost" onClick={onRemove}>
            Удалить
          </Button>
        </div>
      )}
    </li>
  );
}

// `onEdit` and `onRemove` are absent when the attempt cannot be edited.
export function CommentList({
  comments,
  onEdit,
  onRemove,
}: {
  comments: (DraftComment & { id?: string })[];
  onEdit?: (i: number, text: string) => void;
  onRemove?: (i: number) => void;
}) {
  if (comments.length === 0)
    return (
      <p className="text-sm text-muted-foreground">
        {onEdit
          ? "Замечаний пока нет. Выберите строки в коде (Shift+клик — диапазон)."
          : "Замечаний не было."}
      </p>
    );
  return (
    <ul className="space-y-2">
      {comments.map((c, i) => (
        <Item
          // an open editor belongs to its comment, not to a position: deleting an earlier one must not move it
          key={c.id ?? i}
          comment={c}
          onEdit={onEdit && ((t) => onEdit(i, t))}
          onRemove={onRemove && (() => onRemove(i))}
        />
      ))}
    </ul>
  );
}

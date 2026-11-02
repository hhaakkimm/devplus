"use client";

import {
  commentsOnLine,
  overlaps,
  type LineRange,
} from "@/lib/code-review-lines";
import type { DraftComment, Selection } from "@/lib/code-review-state";
import type { HighlightedFile } from "@/lib/code-review";

// The file tree and the read-only code of the open file. A click on a line number selects the line,
// shift-click extends the selection; lines under a comment are marked. Rendered as two grid cells.
export function CodeViewer({
  files,
  active,
  onOpen,
  comments,
  selection,
  onSelect,
}: {
  files: HighlightedFile[];
  active: string;
  onOpen: (path: string) => void;
  comments: DraftComment[];
  selection: Selection | null;
  onSelect?: (file: string, line: number, shift: boolean) => void;
}) {
  const file = files.find((f) => f.path === active) ?? files[0];
  const range: LineRange | null =
    selection?.file === file.path ? selection.range : null;
  return (
    <>
      <nav aria-label="Файлы">
        <ul className="space-y-1">
          {files.map((f) => {
            const n = comments.filter((c) => c.file === f.path).length;
            return (
              <li key={f.path}>
                <button
                  type="button"
                  onClick={() => onOpen(f.path)}
                  aria-current={f.path === file.path}
                  className="w-full rounded-md px-2 py-1 text-left font-mono text-sm outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 aria-[current=true]:bg-muted aria-[current=true]:font-medium"
                >
                  {f.path}
                  {n > 0 && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      {n}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      <div
        role="region"
        tabIndex={0}
        aria-label={`Код ${file.path}`}
        // a long file scrolls inside the box, so the page stays put while a comment is written
        className="max-h-[70vh] min-w-0 overflow-auto rounded-lg border bg-muted/30 py-2 font-mono text-sm"
      >
        {file.lines.map((l) => {
          const marked = commentsOnLine(comments, file.path, l.n).length > 0;
          const selected = range ? overlaps(range, line(l.n)) : false;
          return (
            <div
              key={l.n}
              className={`flex ${selected ? "bg-primary/15" : marked ? "bg-amber-500/15" : ""}`}
            >
              {onSelect ? (
                <button
                  type="button"
                  onClick={(e) => onSelect(file.path, l.n, e.shiftKey)}
                  aria-label={`Строка ${l.n}${marked ? ", есть замечание" : ""}`}
                  aria-pressed={selected}
                  className="w-14 shrink-0 cursor-pointer pr-3 text-right text-muted-foreground outline-none select-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  {l.n}
                </button>
              ) : (
                <span className="w-14 shrink-0 pr-3 text-right text-muted-foreground select-none">
                  {l.n}
                </span>
              )}
              <code className="whitespace-pre">
                {l.tokens.map((t, i) => (
                  <span key={i} style={{ color: t.color }}>
                    {t.text}
                  </span>
                ))}
              </code>
            </div>
          );
        })}
      </div>
    </>
  );
}

const line = (n: number) => ({ line_start: n, line_end: n });

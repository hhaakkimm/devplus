import { dateText, scoreText } from "@/lib/runs";
import type { Attempt } from "@/lib/simulator";

// The user's attempts, newest first; a click shows the attempt's scheme on the canvas.
export function Attempts({
  attempts,
  shown,
  onOpen,
}: {
  attempts: Attempt[];
  shown?: string;
  onOpen: (attempt: Attempt) => void;
}) {
  if (attempts.length === 0)
    return <p className="text-sm text-muted-foreground">Попыток пока нет.</p>;
  return (
    <ul className="divide-y">
      {attempts.map((a) => (
        <li key={a.id}>
          <button
            type="button"
            aria-pressed={a.id === shown}
            onClick={() => onOpen(a)}
            className={`w-full px-2 py-2 text-left text-sm hover:bg-muted ${a.id === shown ? "bg-muted" : ""}`}
          >
            <span className="font-medium">{dateText(a.created_at)}</span>{" "}
            <span className="text-muted-foreground">
              · Балл: {scoreText(a.score)} ·{" "}
              {a.passed ? "Зачтено" : "Не зачтено"}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

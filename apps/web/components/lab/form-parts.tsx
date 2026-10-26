export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-1.5">
      <label className="grid gap-1.5 text-sm font-medium">
        {label}
        {children}
      </label>
      {hint && (
        <p aria-live="polite" className="text-sm text-muted-foreground">
          {hint}
        </p>
      )}
    </div>
  );
}

export function ErrorList({ messages }: { messages: string[] }) {
  if (messages.length === 0) return null;
  return (
    <ul
      role="alert"
      className="list-disc space-y-1 pl-5 text-sm text-destructive"
    >
      {messages.map((m, i) => (
        <li key={i}>{m}</li>
      ))}
    </ul>
  );
}

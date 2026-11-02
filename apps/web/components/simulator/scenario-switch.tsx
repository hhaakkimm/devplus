import type { RunOut } from "@/lib/simulator";

// Which open scenario of the last run colours the nodes by load and labels them «λ / μ rps».
export function ScenarioSwitch({
  scenarios,
  value,
  onChange,
}: {
  scenarios: RunOut["scenarios"];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      Сценарий на схеме
      <select
        className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm dark:bg-input/30"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {scenarios.map((s) => (
          <option key={s.id} value={s.id}>
            {s.title}
          </option>
        ))}
      </select>
    </label>
  );
}

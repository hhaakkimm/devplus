import Link from "next/link";
import { loadReviewTasks } from "@/lib/code-review";

const STATUS = {
  not_started: "Не начата",
  attempted: "Попытка",
  passed: "Зачёт",
} as const;

export default async function CodeReviewPage() {
  const tasks = await loadReviewTasks();
  return (
    <>
      <h1 className="text-3xl font-semibold">Code Review</h1>
      <p className="mt-2 text-muted-foreground">
        Найдите проблемы в чужом коде и вынесите вердикт.
      </p>
      {tasks.length === 0 ? (
        <p className="mt-6 text-muted-foreground">Задач пока нет.</p>
      ) : (
        <table className="mt-6 w-full text-left text-sm">
          <thead>
            <tr className="border-b text-muted-foreground">
              <th className="py-2 font-medium">Задача</th>
              <th className="py-2 font-medium">Сложность</th>
              <th className="py-2 font-medium">Время</th>
              <th className="py-2 font-medium">Статус</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={`${t.module}/${t.slug}`} className="border-b">
                <td className="py-2">
                  <Link
                    href={`/code-review/${t.module}/${t.slug}`}
                    className="font-medium hover:underline"
                  >
                    {t.title}
                  </Link>
                </td>
                <td className="py-2">
                  <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                    {t.difficulty}
                  </span>
                </td>
                <td className="py-2">{t.estimate_min} мин</td>
                <td className="py-2">{STATUS[t.status]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

import { ReviewForm } from "@/components/review/review-form";
import { loadPrompts } from "@/lib/evals";
import { requireUser } from "@/lib/session";

export default async function ReviewPage() {
  const [user, prompts] = await Promise.all([requireUser(), loadPrompts()]);
  return (
    <>
      <h1 className="text-3xl font-semibold">Ревью промпта</h1>
      <p className="mt-2 mb-6 text-muted-foreground">
        Критик оценит промпт по пяти разделам, найдёт проблемы и перепишет его.
      </p>
      <ReviewForm prompts={prompts} login={user.login} />
    </>
  );
}

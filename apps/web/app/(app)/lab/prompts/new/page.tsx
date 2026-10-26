import { PromptForm } from "@/components/lab/prompt-form";

export default function NewPromptPage() {
  return (
    <>
      <h1 className="text-3xl font-semibold">Новый промпт</h1>
      <div className="mt-6">
        <PromptForm />
      </div>
    </>
  );
}

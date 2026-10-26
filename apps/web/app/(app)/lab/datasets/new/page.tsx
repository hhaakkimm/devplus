import { NewDatasetForm } from "@/components/lab/new-dataset-form";

export default function NewDatasetPage() {
  return (
    <>
      <h1 className="text-3xl font-semibold">Новый датасет</h1>
      <div className="mt-6">
        <NewDatasetForm />
      </div>
    </>
  );
}

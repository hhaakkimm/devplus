from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, Response

from app.modules.auth.service import CurrentUser
from app.modules.evals.schemas import (
    MAX_JSONL_BYTES,
    CaseIn,
    CaseOut,
    DatasetDetailOut,
    DatasetIn,
    DatasetPatch,
    DatasetSummaryOut,
    ImportOut,
    PromptDetailOut,
    PromptIn,
    PromptPatch,
    PromptSummaryOut,
    VersionIn,
    VersionOut,
)
from app.modules.evals.service import DatasetService, PromptService

router = APIRouter(prefix="/api/evals", route_class=DishkaRoute)


@router.post("/prompts", status_code=201)
async def create_prompt(
    body: PromptIn, user: FromDishka[CurrentUser], prompts: FromDishka[PromptService]
) -> PromptDetailOut:
    return await prompts.create(user, body.name, body.version)


@router.get("/prompts")
async def list_prompts(
    user: FromDishka[CurrentUser], prompts: FromDishka[PromptService]
) -> list[PromptSummaryOut]:
    return await prompts.list(user)


@router.get("/prompts/{prompt_id}")
async def get_prompt(
    prompt_id: UUID, user: FromDishka[CurrentUser], prompts: FromDishka[PromptService]
) -> PromptDetailOut:
    return await prompts.get(user, prompt_id)


@router.patch("/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: UUID,
    body: PromptPatch,
    user: FromDishka[CurrentUser],
    prompts: FromDishka[PromptService],
) -> PromptSummaryOut:
    return await prompts.update(user, prompt_id, body.name, body.shared)


@router.post("/prompts/{prompt_id}/versions", status_code=201)
async def add_version(
    prompt_id: UUID,
    body: VersionIn,
    user: FromDishka[CurrentUser],
    prompts: FromDishka[PromptService],
) -> VersionOut:
    return await prompts.add_version(user, prompt_id, body)


@router.post("/prompts/{prompt_id}/copy", status_code=201)
async def copy_prompt(
    prompt_id: UUID, user: FromDishka[CurrentUser], prompts: FromDishka[PromptService]
) -> PromptDetailOut:
    return await prompts.copy(user, prompt_id)


@router.post("/datasets", status_code=201)
async def create_dataset(
    body: DatasetIn, user: FromDishka[CurrentUser], datasets: FromDishka[DatasetService]
) -> DatasetDetailOut:
    return await datasets.create(user, body.name)


@router.get("/datasets")
async def list_datasets(
    user: FromDishka[CurrentUser], datasets: FromDishka[DatasetService]
) -> list[DatasetSummaryOut]:
    return await datasets.list(user)


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: UUID, user: FromDishka[CurrentUser], datasets: FromDishka[DatasetService]
) -> DatasetDetailOut:
    return await datasets.get(user, dataset_id)


@router.patch("/datasets/{dataset_id}")
async def update_dataset(
    dataset_id: UUID,
    body: DatasetPatch,
    user: FromDishka[CurrentUser],
    datasets: FromDishka[DatasetService],
) -> DatasetSummaryOut:
    return await datasets.update(user, dataset_id, body.name, body.shared)


@router.post("/datasets/{dataset_id}/copy", status_code=201)
async def copy_dataset(
    dataset_id: UUID, user: FromDishka[CurrentUser], datasets: FromDishka[DatasetService]
) -> DatasetDetailOut:
    return await datasets.copy(user, dataset_id)


@router.get("/datasets/{dataset_id}/export", response_class=Response)
async def export_dataset(
    dataset_id: UUID, user: FromDishka[CurrentUser], datasets: FromDishka[DatasetService]
) -> Response:
    return Response(
        await datasets.export_jsonl(user, dataset_id), media_type="application/x-ndjson"
    )


@router.put(
    "/datasets/{dataset_id}/cases",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/x-ndjson": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def import_cases(
    dataset_id: UUID,
    request: Request,
    user: FromDishka[CurrentUser],
    datasets: FromDishka[DatasetService],
) -> ImportOut:
    # raw JSONL, not JSON: read the stream by hand and stop buffering past the limit;
    # the service rejects the oversize input
    raw = bytearray()
    async for chunk in request.stream():
        raw += chunk
        if len(raw) > MAX_JSONL_BYTES:
            break
    return ImportOut(count=await datasets.replace_cases(user, dataset_id, bytes(raw)))


@router.post("/datasets/{dataset_id}/cases", status_code=201)
async def add_case(
    dataset_id: UUID,
    body: CaseIn,
    user: FromDishka[CurrentUser],
    datasets: FromDishka[DatasetService],
) -> CaseOut:
    return await datasets.add_case(user, dataset_id, body)


@router.put("/datasets/{dataset_id}/cases/{case_id}")
async def update_case(
    dataset_id: UUID,
    case_id: UUID,
    body: CaseIn,
    user: FromDishka[CurrentUser],
    datasets: FromDishka[DatasetService],
) -> CaseOut:
    return await datasets.update_case(user, dataset_id, case_id, body)


@router.delete("/datasets/{dataset_id}/cases/{case_id}", status_code=204)
async def delete_case(
    dataset_id: UUID,
    case_id: UUID,
    user: FromDishka[CurrentUser],
    datasets: FromDishka[DatasetService],
) -> None:
    await datasets.delete_case(user, dataset_id, case_id)

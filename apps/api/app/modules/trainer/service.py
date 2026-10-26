from pathlib import Path

from app.core.config import Settings
from app.core.errors import NotFound, Unprocessable
from app.modules.auth.service import CurrentUser
from app.modules.evals.service import (
    PromptService,
    RunOut,
    RunService,
    VersionIn,
    template_variables,
)
from app.modules.trainer.schemas import AttemptIn, TaskOut
from app.modules.trainer.tasks import TaskSpec, cached_tasks


class TrainerService:
    def __init__(self, settings: Settings, prompts: PromptService, runs: RunService) -> None:
        self.settings = settings
        self.prompts = prompts
        self.runs = runs

    async def submit(self, user: CurrentUser, module: str, slug: str, body: AttemptIn) -> RunOut:
        task = self._task(module, slug)
        if missing := set(task.variables) - template_variables(body.user_template):
            raise Unprocessable(f"В шаблоне нет переменных: {', '.join(sorted(missing))}")
        # model, effort and limit are the task's: the user writes only the texts
        version = VersionIn(
            system=body.system,
            user_template=body.user_template,
            model=task.model,
            effort=task.effort,
            max_tokens=task.max_tokens,
        )
        key = f"{module}/{slug}"
        prompt_id = await self.prompts.trainer_prompt_id(user, key)
        if prompt_id is None:  # the first attempt: a private prompt for the task, version 1
            prompt = await self.prompts.create(user, task.title, version, trainer_task=key)
            version_id = prompt.versions[0].id
        else:
            version_id = (await self.prompts.add_version(user, prompt_id, version)).id
        return await self.runs.create_for(
            user.id,
            version_id,
            task.cases,
            task.graders,
            "trainer",
            task_slug=key,
            pass_threshold=task.pass_threshold,
        )

    async def attempts(self, user: CurrentUser, module: str, slug: str) -> list[RunOut]:
        self._task(module, slug)
        return await self.runs.list_for_task(user.id, f"{module}/{slug}")

    # keep last: this method shadows the builtin `list` in the class body
    async def list(self, user: CurrentUser) -> list[TaskOut]:
        solved = await self.runs.passed_tasks(user.id)
        return [
            TaskOut(
                module=t.module,
                slug=t.slug,
                title=t.title,
                summary=t.summary,
                solved=f"{t.module}/{t.slug}" in solved,
            )
            for t in self._tasks()
        ]

    def _tasks(self) -> tuple[TaskSpec, ...]:
        return cached_tasks(Path(self.settings.content_dir))

    def _task(self, module: str, slug: str) -> TaskSpec:
        for task in self._tasks():
            if (task.module, task.slug) == (module, slug):
                return task
        raise NotFound("Не найдено")

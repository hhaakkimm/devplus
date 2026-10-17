from pydantic import BaseModel

from app.modules.progress.service import CompletedLesson


class ProgressOut(BaseModel):
    completed: list[CompletedLesson]

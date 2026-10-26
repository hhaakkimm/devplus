from pydantic import BaseModel, model_validator

from app.modules.evals.service import MAX_PROMPT_CHARS


class TaskOut(BaseModel):
    module: str
    slug: str
    title: str
    summary: str
    solved: bool


class AttemptIn(BaseModel):
    system: str
    user_template: str

    @model_validator(mode="after")
    def check_limits(self) -> "AttemptIn":
        # the limits of a prompt version, which the attempt becomes
        if len(self.system) + len(self.user_template) > MAX_PROMPT_CHARS:
            raise ValueError(
                f"system и user_template вместе не длиннее {MAX_PROMPT_CHARS} символов"
            )
        if "\x00" in self.system + self.user_template:  # Postgres text cannot hold NUL
            raise ValueError("символ NUL не допускается")
        return self

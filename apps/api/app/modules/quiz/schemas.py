from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from app.modules.quiz.service import QuizResultRow

MAX_QUESTIONS = 200


class QuizResultIn(BaseModel):
    score: Annotated[int, Field(ge=0)]
    total: Annotated[int, Field(ge=1, le=MAX_QUESTIONS)]

    @model_validator(mode="after")
    def score_within_total(self) -> "QuizResultIn":
        if self.score > self.total:
            raise ValueError("score cannot exceed total")
        return self


class QuizResultsOut(BaseModel):
    results: list[QuizResultRow]

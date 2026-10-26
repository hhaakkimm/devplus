from typing import Protocol
from uuid import UUID

from app.core.errors import Forbidden, NotFound


class Owned(Protocol):
    owner_id: UUID


class Shareable(Owned, Protocol):
    shared: bool


def can_view(obj: Shareable, user_id: UUID) -> bool:
    if obj.owner_id == user_id:
        return True
    # Trainer prompts stay private whatever `shared` says
    return obj.shared and getattr(obj, "trainer_task", None) is None


def require_view[T: Shareable](obj: T | None, user_id: UUID) -> T:
    # same 404 for "missing" and "no access", so existence is not leaked
    if obj is None or not can_view(obj, user_id):
        raise NotFound("Не найдено")
    return obj


def require_edit[T: Shareable](obj: T | None, user_id: UUID) -> T:
    obj = require_view(obj, user_id)
    if obj.owner_id != user_id:
        raise Forbidden("Только автор может изменять")
    return obj


def require_view_run[T: Owned](run: T | None, prompt_owner_id: UUID | None, user_id: UUID) -> T:
    # a run is seen by whoever started it and by the author of its prompt, even if not shared
    if run is None or user_id not in (run.owner_id, prompt_owner_id):
        raise NotFound("Не найдено")
    return run

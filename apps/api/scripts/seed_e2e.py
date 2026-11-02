"""Seed the e2e user with a fresh session and print the raw token to stdout."""

import asyncio
import os
import secrets
import sys
from pathlib import Path

# Run as a plain script: the project is not installed, so make `app` importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main() -> None:
    from sqlalchemy import delete, func
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.modules.auth.models import User, UserSession
    from app.modules.auth.service import SESSION_TTL, hash_token
    from app.modules.progress.models import LessonProgress
    from app.modules.simulator.models import SimAttempt

    engine = create_async_engine(os.environ["DATABASE_URL"])
    token = secrets.token_urlsafe(32)
    async with engine.begin() as conn:
        new = insert(User).values(github_id=-1, login="e2e-user", name="E2E")
        user_id = await conn.scalar(
            new.on_conflict_do_update(
                index_elements=[User.github_id],
                set_={"login": new.excluded.login, "name": new.excluded.name},
            ).returning(User.id)
        )
        await conn.execute(delete(LessonProgress).where(LessonProgress.user_id == user_id))
        # the simulator spec expects one attempt, and the daily limit of 20 would stop daily runs
        await conn.execute(delete(SimAttempt).where(SimAttempt.user_id == user_id))
        await conn.execute(delete(UserSession).where(UserSession.user_id == user_id))
        await conn.execute(
            insert(UserSession).values(
                token_hash=hash_token(token),
                user_id=user_id,
                expires_at=func.now() + SESSION_TTL,
            )
        )
    await engine.dispose()
    print(token)


asyncio.run(main())

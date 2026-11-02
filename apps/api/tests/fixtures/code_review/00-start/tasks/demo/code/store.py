"""Job store on top of sqlite."""

import sqlite3


class JobStore:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row

    def next_pending(self) -> dict | None:
        row = self.db.execute("SELECT * FROM jobs WHERE status = 'pending' LIMIT 1").fetchone()
        return dict(row) if row else None

    def mark(self, job_id: int, status: str) -> None:
        self.db.execute(f"UPDATE jobs SET status = '{status}' WHERE id = {job_id}")
        self.db.commit()

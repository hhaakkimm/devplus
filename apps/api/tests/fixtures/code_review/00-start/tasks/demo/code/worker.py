"""Background worker: claims pending jobs from the store and runs them."""

import threading
import time

from store import JobStore

POLL_SECONDS = 1.0


class Worker:
    def __init__(self, store: JobStore) -> None:
        self.store = store
        self.lock = threading.Lock()
        self.running = True

    def claim(self) -> dict | None:
        job = self.store.next_pending()
        if job is None:
            return None
        with self.lock:
            self.store.mark(job["id"], "running")
        return job

    def run_forever(self) -> None:
        while self.running:
            job = self.claim()
            if job is None:
                time.sleep(POLL_SECONDS)
                continue
            self.store.mark(job["id"], "done")

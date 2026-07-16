"""Background worker pool for parallel Gemini extraction."""
from __future__ import annotations

import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from llm import gemini_client
from pipeline.knowledge import merge_extraction
from storage.repository import Repository


class ExtractionQueue:
    """Continuously claims unextracted docs and processes them in parallel."""

    def __init__(
        self,
        repo: Repository,
        startup_context: dict[str, Any],
        *,
        batch_size: int = 8,
        workers: int = 3,
        poll_interval: float = 0.3,
    ):
        self.repo = repo
        self.startup_context = startup_context
        self.batch_size = batch_size
        self.workers = max(1, workers)
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._idle = threading.Event()
        self._idle.set()
        self._active = 0
        self._active_lock = threading.Lock()
        self._processed_batches = 0
        self._executor: ThreadPoolExecutor | None = None

    def start(self) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=self.workers,
            thread_name_prefix="extract",
        )
        for _ in range(self.workers):
            self._executor.submit(self._worker_loop)
        print(f"[extractor] started {self.workers} worker(s)", file=sys.stderr)

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            docs = self.repo.claim_unextracted_documents(self.batch_size)
            if not docs:
                with self._active_lock:
                    if self._active == 0:
                        self._idle.set()
                if self._stop.is_set():
                    break
                time.sleep(self.poll_interval)
                continue

            with self._active_lock:
                self._active += 1
                self._idle.clear()

            try:
                extraction = gemini_client.extract_knowledge_from_documents(
                    docs, self.startup_context
                )
                doc_map = {d["id"]: d for d in docs}
                doc_ids = list(doc_map.keys())
                merge_extraction(self.repo, extraction, doc_map)
                self.repo.mark_documents_extracted(doc_ids)
                self._processed_batches += 1
            except Exception as e:
                print(f"[extractor] batch failed: {e}", file=sys.stderr)
                self.repo.release_claimed_documents([d["id"] for d in docs])
            finally:
                with self._active_lock:
                    self._active -= 1
                    if self._active == 0 and not self.repo.has_unextracted_documents():
                        self._idle.set()

    def wait_until_drained(self, timeout: float = 600.0) -> None:
        """Block until no unextracted documents remain and workers are idle."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.repo.has_unextracted_documents():
                with self._active_lock:
                    if self._active == 0:
                        return
            self._idle.wait(timeout=0.5)
        print("[extractor] warning: drain timeout — continuing", file=sys.stderr)

    def stop(self) -> None:
        self._stop.set()
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=False)
        print(
            f"[extractor] stopped ({self._processed_batches} batches processed)",
            file=sys.stderr,
        )

    @property
    def processed_batches(self) -> int:
        return self._processed_batches

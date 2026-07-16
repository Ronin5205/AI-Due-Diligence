"""Execute search queries across sources and persist documents."""
from __future__ import annotations

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from schemas.analyzer import RawDocument
from sources.base import RawDocumentRecord, SearchSource
from storage.repository import Repository


class Collector:
    def __init__(
        self,
        repo: Repository,
        sources: dict[str, SearchSource],
        limit_per_query: int = 8,
        search_workers: int = 8,
    ):
        self.repo = repo
        self.sources = sources
        self.limit_per_query = limit_per_query
        self.search_workers = max(1, search_workers)
        self.sources_used: set[str] = set()
        self.sources_skipped: set[str] = set()
        self._lock = threading.Lock()

    def run_pending(self, depth: int | None = None) -> int:
        return self.run_pending_parallel(depth=depth)

    def run_pending_parallel(self, depth: int | None = None) -> int:
        pending = self.repo.get_pending_queries(depth=depth)
        if not pending:
            return 0

        print(
            f"[collector] running {len(pending)} searches with {self.search_workers} workers",
            file=sys.stderr,
        )
        new_docs = 0

        with ThreadPoolExecutor(
            max_workers=min(self.search_workers, len(pending)),
            thread_name_prefix="search",
        ) as pool:
            futures = {
                pool.submit(self._execute_search, item): item for item in pending
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    source_name, records, status = future.result()
                except Exception as e:
                    print(f"[collector] {item['source']} failed: {e}", file=sys.stderr)
                    with self._lock:
                        self.repo.mark_query_done(item["id"], status="error")
                    continue

                with self._lock:
                    if status == "skipped":
                        self.sources_skipped.add(source_name)
                        self.repo.mark_query_done(item["id"], status="skipped")
                        continue

                    self.sources_used.add(source_name)
                    for rec in records:
                        doc = RawDocument(
                            source=rec.source,
                            external_id=rec.external_id,
                            title=rec.title,
                            content=rec.content,
                            url=rec.url,
                            query=item["query"],
                            depth=item["depth"],
                            metadata=rec.metadata,
                        )
                        if self.repo.insert_document(doc):
                            new_docs += 1
                    self.repo.mark_query_done(item["id"], status="done")

        return new_docs

    def _execute_search(
        self, item: dict[str, Any]
    ) -> tuple[str, list[RawDocumentRecord], str]:
        source_name = item["source"]
        source = self.sources.get(source_name)
        if source is None:
            return source_name, [], "skipped"
        if not source.is_configured():
            return source_name, [], "skipped"

        records = source.search(item["query"], limit=self.limit_per_query)
        return source_name, records, "done"

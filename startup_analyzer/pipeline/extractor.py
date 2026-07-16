"""Extract knowledge from raw documents using Gemini (sync fallback)."""
from __future__ import annotations

from typing import Any

from llm import gemini_client
from pipeline.knowledge import merge_extraction
from storage.repository import Repository


class Extractor:
    """Synchronous single-threaded extractor (used as fallback)."""

    def __init__(self, repo: Repository, batch_size: int = 8):
        self.repo = repo
        self.batch_size = batch_size

    def run(self, startup_context: dict[str, Any]) -> dict[str, list[Any]]:
        all_extracted: dict[str, list[Any]] = {
            "companies": [],
            "problems": [],
            "features": [],
            "technologies": [],
            "market_signals": [],
            "success_indicators": [],
            "failure_patterns": [],
            "relations": [],
        }

        while True:
            docs = self.repo.claim_unextracted_documents(self.batch_size)
            if not docs:
                break

            extraction = gemini_client.extract_knowledge_from_documents(docs, startup_context)
            doc_ids = [d["id"] for d in docs]
            doc_map = {d["id"]: d for d in docs}

            merge_extraction(self.repo, extraction, doc_map)
            self.repo.mark_documents_extracted(doc_ids)

            for key in all_extracted:
                items = extraction.get(key, [])
                if isinstance(items, list):
                    all_extracted[key].extend(items)

        return all_extracted

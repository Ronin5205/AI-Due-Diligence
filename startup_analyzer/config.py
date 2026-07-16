"""Environment-driven configuration for the analyzer pipeline."""
from __future__ import annotations

import os
from dataclasses import dataclass

from storage.database_url import resolve_database_url


@dataclass(frozen=True)
class AnalyzerConfig:
    database_url: str
    gemini_api_key: str
    gemini_model: str
    gemini_max_rpm: int
    max_depth: int
    queries_per_source_depth0: int
    queries_per_source_depth_n: int
    extraction_batch_size: int
    search_workers: int
    extraction_workers: int
    github_token: str
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    product_hunt_token: str
    http_timeout: float
    sources: list[str] | None
    flush_db_after_run: bool


def load_config(
    *,
    max_depth: int | None = None,
    queries_per_source: int | None = None,
    sources: list[str] | None = None,
    flush_db_after_run: bool | None = None,
) -> AnalyzerConfig:
    return AnalyzerConfig(
        database_url=resolve_database_url(),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        gemini_max_rpm=int(os.environ.get("GEMINI_MAX_RPM", "20")),
        max_depth=max_depth or int(os.environ.get("ANALYZER_MAX_DEPTH", "4")),
        queries_per_source_depth0=queries_per_source or int(
            os.environ.get("ANALYZER_QUERIES_PER_SOURCE", "5")
        ),
        queries_per_source_depth_n=max(1, (queries_per_source or int(
            os.environ.get("ANALYZER_QUERIES_PER_SOURCE", "5")
        )) - 2),
        extraction_batch_size=int(os.environ.get("ANALYZER_EXTRACTION_BATCH", "8")),
        search_workers=int(os.environ.get("ANALYZER_SEARCH_WORKERS", "8")),
        extraction_workers=int(os.environ.get("ANALYZER_EXTRACTION_WORKERS", "3")),
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        reddit_client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
        reddit_client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
        reddit_user_agent=os.environ.get("REDDIT_USER_AGENT", "startup-analyzer/1.0"),
        product_hunt_token=os.environ.get("PRODUCT_HUNT_TOKEN", ""),
        http_timeout=float(os.environ.get("ANALYZER_HTTP_TIMEOUT", "30")),
        sources=sources,
        flush_db_after_run=(
            flush_db_after_run
            if flush_db_after_run is not None
            else os.environ.get("ANALYZER_FLUSH_DB_AFTER_RUN", "true").lower() in ("1", "true", "yes")
        ),
    )


DEFAULT_SOURCES = [
    "reddit",
    "hackernews",
    "github",
    "product_hunt",
    "google_trends",
]

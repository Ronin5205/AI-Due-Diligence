"""Generate follow-up queries from knowledge graph at depth 2-4."""
from __future__ import annotations

from typing import Any

from llm import gemini_client
from schemas.analyzer import SearchQueryItem


def expand_queries_for_depth(
    entities: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    startup_context: dict[str, Any],
    enabled_sources: list[str],
    depth: int,
    existing_queries: set[str],
    limit_per_source: int,
) -> list[SearchQueryItem]:
    ai_queries = gemini_client.expand_queries(
        entities=entities,
        relations=relations,
        startup_context=startup_context,
        enabled_sources=enabled_sources,
        depth=depth,
        existing_queries=list(existing_queries),
    )

    result: list[SearchQueryItem] = []
    per_source: dict[str, int] = {}

    for q in ai_queries:
        source = q["source"]
        if per_source.get(source, 0) >= limit_per_source:
            continue
        key = q["query"].lower()
        if key in existing_queries:
            continue
        result.append(SearchQueryItem(
            query=q["query"],
            source=source,
            depth=depth,
            rationale=q.get("rationale", f"expansion depth {depth}"),
        ))
        per_source[source] = per_source.get(source, 0) + 1
        existing_queries.add(key)

    return result

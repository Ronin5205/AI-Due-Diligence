"""Generate initial and seed-based search queries."""
from __future__ import annotations

from typing import Any

from llm import gemini_client
from schemas.analyzer import SearchQueryItem

# Mirrors startup_interview/graph/question_bank.py PLATFORM_SEED_BUCKETS
PLATFORM_SEED_BUCKETS: dict[str, list[str]] = {
    "reddit": ["keywords", "pain_points", "customer_segments"],
    "hackernews": ["keywords", "pain_points", "technologies"],
    "github": ["technologies", "frameworks", "software", "integrations"],
    "product_hunt": ["companies", "products", "competitors"],
    "google_trends": ["keywords", "industries", "customer_segments"],
}

from llm import gemini_client
from schemas.analyzer import SearchQueryItem


def _profile_dict(startup: Any) -> dict[str, Any]:
    if hasattr(startup, "model_dump"):
        return startup.model_dump()
    return dict(startup)


def _flatten_seeds(seeds: dict[str, list[str]], platform: str) -> list[str]:
    buckets = PLATFORM_SEED_BUCKETS.get(platform, [])
    terms: list[str] = []
    for bucket in buckets:
        for item in seeds.get(bucket, []):
            if item and item not in terms:
                terms.append(item)
    return terms


def _profile_keywords(startup: Any) -> list[str]:
    fields = [
        "startup_idea", "core_problem", "competitors", "alternatives",
        "desired_features", "missing_capabilities", "industry_keywords",
        "technical_terms", "industry_jargon", "why_switch",
    ]
    terms = []
    for f in fields:
        val = getattr(startup, f, None)
        if val and isinstance(val, str) and val.strip():
            terms.append(val.strip())
    return terms


def build_seed_queries(
    startup: Any,
    enabled_sources: list[str],
    depth: int,
    limit_per_source: int,
) -> list[SearchQueryItem]:
    profile = _profile_dict(startup)
    seeds = profile.get("search_seeds", {})
    queries: list[SearchQueryItem] = []
    keywords = _profile_keywords(startup)

    for source in enabled_sources:
        seed_terms = _flatten_seeds(seeds, source)
        combined = seed_terms + keywords
        seen: set[str] = set()
        count = 0
        for term in combined:
            key = term.lower()
            if key in seen or count >= limit_per_source:
                continue
            seen.add(key)
            queries.append(SearchQueryItem(
                query=term[:120],
                source=source,
                depth=depth,
                rationale=f"seed/profile term for {source}",
            ))
            count += 1
    return queries


def generate_initial_queries(
    startup: Any,
    enabled_sources: list[str],
    limit_per_source: int,
    existing_queries: set[str] | None = None,
) -> list[SearchQueryItem]:
    profile = _profile_dict(startup)
    seeds = profile.get("search_seeds", {})

    ai_queries = gemini_client.generate_search_queries(
        startup_profile={k: v for k, v in profile.items() if k != "search_seeds"},
        search_seeds=seeds,
        enabled_sources=enabled_sources,
        depth=0,
        existing_queries=list(existing_queries or []),
    )

    result: list[SearchQueryItem] = []
    per_source: dict[str, int] = {}

    for q in ai_queries:
        source = q["source"]
        if per_source.get(source, 0) >= limit_per_source:
            continue
        key = q["query"].lower()
        if existing_queries and key in existing_queries:
            continue
        result.append(SearchQueryItem(
            query=q["query"],
            source=source,
            depth=0,
            rationale=q.get("rationale", "AI-generated"),
        ))
        per_source[source] = per_source.get(source, 0) + 1

    seed_queries = build_seed_queries(startup, enabled_sources, 0, limit_per_source)
    existing = {r.query.lower() for r in result}
    for sq in seed_queries:
        if sq.query.lower() not in existing and per_source.get(sq.source, 0) < limit_per_source:
            result.append(sq)
            per_source[sq.source] = per_source.get(sq.source, 0) + 1
            existing.add(sq.query.lower())

    return result

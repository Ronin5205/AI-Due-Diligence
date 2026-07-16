"""Merge extracted knowledge into persistent entities."""
from __future__ import annotations

from typing import Any

from schemas.analyzer import KnowledgeEntity, KnowledgeRelation
from storage.repository import Repository


def _entity_from_item(item: dict[str, Any], entity_type: str, doc: dict[str, Any]) -> KnowledgeEntity:
    name = item.get("name") or item.get("signal") or item.get("indicator") or item.get("pattern") or ""
    return KnowledgeEntity(
        entity_type=entity_type,
        name=str(name).strip(),
        description=str(item.get("description") or item.get("signal") or item.get("indicator") or ""),
        confidence=float(item.get("confidence", 0.5)),
        platforms_seen=[doc.get("source", "")],
        evidence_snippets=[str(item.get("evidence_snippet", ""))[:500]],
        evidence_urls=[doc.get("url", "")],
    )


def merge_extraction(
    repo: Repository,
    extraction: dict[str, Any],
    doc_map: dict[int, dict[str, Any]],
) -> None:
    type_map = {
        "companies": "company",
        "problems": "problem",
        "features": "feature",
        "technologies": "technology",
        "market_signals": "market_signal",
        "success_indicators": "success_signal",
        "failure_patterns": "failure_pattern",
    }

    entity_ids: dict[tuple[str, str], int] = repo.get_entity_id_map()

    for bucket, entity_type in type_map.items():
        for item in extraction.get(bucket, []):
            if not isinstance(item, dict):
                continue
            doc_id = next(iter(doc_map), None)
            doc = doc_map.get(doc_id, {}) if doc_id else {}
            entity = _entity_from_item(item, entity_type, doc)
            if not entity.name:
                continue
            eid = repo.upsert_entity(entity, doc_ids=list(doc_map.keys()))
            entity_ids[(entity_type, entity.name.lower())] = eid

    for rel in extraction.get("relations", []):
        if not isinstance(rel, dict):
            continue
        source_type = str(rel.get("source_type", "entity"))
        target_type = str(rel.get("target_type", "entity"))
        source_name = str(rel.get("source_name", "")).strip()
        target_name = str(rel.get("target_name", "")).strip()
        if not source_name or not target_name:
            continue

        sid = entity_ids.get((source_type, source_name.lower()))
        tid = entity_ids.get((target_type, target_name.lower()))
        if sid is None:
            sid = repo.upsert_entity(KnowledgeEntity(entity_type=source_type, name=source_name))
            entity_ids[(source_type, source_name.lower())] = sid
        if tid is None:
            tid = repo.upsert_entity(KnowledgeEntity(entity_type=target_type, name=target_name))
            entity_ids[(target_type, target_name.lower())] = tid

        repo.upsert_relation(
            KnowledgeRelation(
                source_name=source_name,
                source_type=source_type,
                target_name=target_name,
                target_type=target_type,
                relation_type=str(rel.get("relation_type", "related_to")),
                confidence=float(rel.get("confidence", 0.5)),
            ),
            source_id=sid,
            target_id=tid,
            doc_ids=list(doc_map.keys()),
        )


def build_structured_knowledge(entities: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {
        "companies": [],
        "problems": [],
        "features": [],
        "technologies": [],
        "market_signals": [],
        "success_indicators": [],
        "failure_patterns": [],
    }
    type_to_bucket = {
        "company": "companies",
        "problem": "problems",
        "feature": "features",
        "technology": "technologies",
        "market_signal": "market_signals",
        "success_signal": "success_indicators",
        "failure_pattern": "failure_patterns",
    }
    for e in entities:
        bucket = type_to_bucket.get(e.get("entity_type", ""))
        if bucket:
            result[bucket].append({
                "name": e.get("name"),
                "description": e.get("description"),
                "confidence": e.get("confidence"),
                "mention_count": e.get("mention_count"),
                "platforms_seen": e.get("platforms_seen"),
            })
    return result

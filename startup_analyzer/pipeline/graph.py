"""Build knowledge graph from entities and relations."""
from __future__ import annotations

from typing import Any

from schemas.analyzer import GraphEdge, GraphNode


class KnowledgeGraph:
    def __init__(self, startup_name: str = ""):
        self.startup_name = startup_name
        self._searched_entities: set[str] = set()

    def mark_searched(self, term: str) -> None:
        self._searched_entities.add(term.lower())

    def build(
        self,
        entities: list[dict[str, Any]],
        relations: list[dict[str, Any]],
    ) -> dict[str, list[Any]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_nodes: set[str] = set()

        if self.startup_name:
            sid = f"startup:{self.startup_name}"
            nodes.append(GraphNode(
                id=sid,
                type="startup",
                label=self.startup_name,
                confidence=1.0,
                mention_count=1,
            ))
            seen_nodes.add(sid)

        for e in entities:
            nid = f"{e['entity_type']}:{e['name']}"
            if nid in seen_nodes:
                continue
            seen_nodes.add(nid)
            nodes.append(GraphNode(
                id=nid,
                type=e["entity_type"],
                label=e["name"],
                confidence=float(e.get("confidence", 0.5)),
                mention_count=int(e.get("mention_count", 1)),
            ))

        for r in relations:
            src = f"{r['source_type']}:{r['source_name']}"
            tgt = f"{r['target_type']}:{r['target_name']}"
            edges.append(GraphEdge(
                source=src,
                target=tgt,
                relation=r["relation_type"],
                confidence=float(r.get("confidence", 0.5)),
            ))

        return {
            "nodes": [n.model_dump() for n in nodes],
            "edges": [e.model_dump() for e in edges],
        }

    def get_expansion_candidates(self, entities: list[dict[str, Any]], limit: int = 15) -> list[dict[str, Any]]:
        candidates = []
        priority_types = {"company", "problem", "market_signal", "technology"}
        for e in entities:
            if e.get("entity_type") not in priority_types:
                continue
            name = e.get("name", "")
            if name.lower() in self._searched_entities:
                continue
            candidates.append(e)
        candidates.sort(key=lambda x: (x.get("confidence", 0), x.get("mention_count", 0)), reverse=True)
        return candidates[:limit]

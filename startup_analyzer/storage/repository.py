"""CRUD operations for analysis runs, documents, and knowledge."""
from __future__ import annotations

import json
from typing import Any

from schemas.analyzer import KnowledgeEntity, KnowledgeRelation, RawDocument, SearchQueryItem
from storage.db import get_connection


class Repository:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.run_id: int | None = None
        self.session_id: str = ""

    def create_run(self, session_id: str, max_depth: int) -> int:
        self.session_id = session_id
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analysis_runs (session_id, max_depth, status)
                    VALUES (%s, %s, 'running')
                    RETURNING id
                    """,
                    (session_id, max_depth),
                )
                row = cur.fetchone()
                self.run_id = row[0]
                return self.run_id

    def finish_run(self, status: str = "completed", metadata: dict | None = None) -> None:
        if self.run_id is None:
            return
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE analysis_runs
                    SET status = %s, finished_at = NOW(), metadata = %s::jsonb
                    WHERE id = %s
                    """,
                    (status, json.dumps(metadata or {}), self.run_id),
                )

    def insert_queries(self, queries: list[SearchQueryItem]) -> list[int]:
        if self.run_id is None:
            return []
        ids: list[int] = []
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                for q in queries:
                    cur.execute(
                        """
                        INSERT INTO search_queries (run_id, session_id, query, source, depth, rationale, status)
                        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                        ON CONFLICT (run_id, source, query, depth) DO NOTHING
                        RETURNING id
                        """,
                        (self.run_id, self.session_id, q.query, q.source, q.depth, q.rationale),
                    )
                    row = cur.fetchone()
                    if row:
                        ids.append(row[0])
        return ids

    def get_pending_queries(self, depth: int | None = None) -> list[dict[str, Any]]:
        if self.run_id is None:
            return []
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                if depth is not None:
                    cur.execute(
                        """
                        SELECT id, query, source, depth, rationale
                        FROM search_queries
                        WHERE run_id = %s AND status = 'pending' AND depth = %s
                        ORDER BY id
                        """,
                        (self.run_id, depth),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, query, source, depth, rationale
                        FROM search_queries
                        WHERE run_id = %s AND status = 'pending'
                        ORDER BY depth, id
                        """,
                        (self.run_id,),
                    )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def mark_query_done(self, query_id: int, status: str = "done") -> None:
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE search_queries SET status = %s WHERE id = %s",
                    (status, query_id),
                )

    def insert_document(self, doc: RawDocument) -> int | None:
        if self.run_id is None:
            return None
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO raw_documents
                        (run_id, session_id, source, external_id, query, depth,
                         title, content, url, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (session_id, source, external_id) DO NOTHING
                    RETURNING id
                    """,
                    (
                        self.run_id,
                        self.session_id,
                        doc.source,
                        doc.external_id,
                        doc.query,
                        doc.depth,
                        doc.title,
                        doc.content,
                        doc.url,
                        json.dumps(doc.metadata),
                    ),
                )
                row = cur.fetchone()
                return row[0] if row else None

    def get_unextracted_documents(self, limit: int = 50) -> list[dict[str, Any]]:
        if self.run_id is None:
            return []
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, source, external_id, title, content, url, query, depth, metadata
                    FROM raw_documents
                    WHERE run_id = %s AND extracted = FALSE
                    ORDER BY id
                    LIMIT %s
                    """,
                    (self.run_id, limit),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def mark_documents_extracted(self, doc_ids: list[int]) -> None:
        if not doc_ids:
            return
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE raw_documents SET extracted = TRUE WHERE id = ANY(%s)",
                    (doc_ids,),
                )

    def count_documents(self) -> int:
        if self.run_id is None:
            return 0
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM raw_documents WHERE run_id = %s",
                    (self.run_id,),
                )
                return cur.fetchone()[0]

    def count_queries(self) -> int:
        if self.run_id is None:
            return 0
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM search_queries WHERE run_id = %s",
                    (self.run_id,),
                )
                return cur.fetchone()[0]

    def get_executed_query_texts(self) -> set[str]:
        if self.run_id is None:
            return set()
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT LOWER(query) FROM search_queries WHERE run_id = %s",
                    (self.run_id,),
                )
                return {row[0] for row in cur.fetchall()}

    def upsert_entity(self, entity: KnowledgeEntity, doc_ids: list[int] | None = None) -> int:
        if self.run_id is None:
            return 0
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO knowledge_entities
                        (run_id, session_id, entity_type, name, description, confidence,
                         mention_count, platforms_seen, evidence_doc_ids, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                    ON CONFLICT (run_id, entity_type, name) DO UPDATE SET
                        description = CASE
                            WHEN EXCLUDED.description != '' THEN EXCLUDED.description
                            ELSE knowledge_entities.description
                        END,
                        confidence = GREATEST(knowledge_entities.confidence, EXCLUDED.confidence),
                        mention_count = knowledge_entities.mention_count + EXCLUDED.mention_count,
                        platforms_seen = (
                            SELECT jsonb_agg(DISTINCT elem)
                            FROM jsonb_array_elements(
                                knowledge_entities.platforms_seen || EXCLUDED.platforms_seen
                            ) elem
                        ),
                        evidence_doc_ids = (
                            SELECT jsonb_agg(DISTINCT elem)
                            FROM jsonb_array_elements(
                                knowledge_entities.evidence_doc_ids || EXCLUDED.evidence_doc_ids
                            ) elem
                        )
                    RETURNING id
                    """,
                    (
                        self.run_id,
                        self.session_id,
                        entity.entity_type,
                        entity.name,
                        entity.description,
                        entity.confidence,
                        entity.mention_count,
                        json.dumps(entity.platforms_seen),
                        json.dumps(doc_ids or []),
                        json.dumps(entity.metadata),
                    ),
                )
                return cur.fetchone()[0]

    def upsert_relation(
        self,
        relation: KnowledgeRelation,
        source_id: int,
        target_id: int,
        doc_ids: list[int] | None = None,
    ) -> None:
        if self.run_id is None:
            return
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO knowledge_relations
                        (run_id, session_id, source_entity_id, target_entity_id,
                         relation_type, confidence, evidence_doc_ids)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (run_id, source_entity_id, target_entity_id, relation_type) DO UPDATE SET
                        confidence = GREATEST(knowledge_relations.confidence, EXCLUDED.confidence)
                    """,
                    (
                        self.run_id,
                        self.session_id,
                        source_id,
                        target_id,
                        relation.relation_type,
                        relation.confidence,
                        json.dumps(doc_ids or []),
                    ),
                )

    def get_all_entities(self) -> list[dict[str, Any]]:
        if self.run_id is None:
            return []
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, entity_type, name, description, confidence,
                           mention_count, platforms_seen, evidence_doc_ids, metadata
                    FROM knowledge_entities WHERE run_id = %s
                    ORDER BY confidence DESC, mention_count DESC
                    """,
                    (self.run_id,),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_all_relations(self) -> list[dict[str, Any]]:
        if self.run_id is None:
            return []
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.id, r.relation_type, r.confidence, r.evidence_doc_ids,
                           se.name AS source_name, se.entity_type AS source_type,
                           te.name AS target_name, te.entity_type AS target_type
                    FROM knowledge_relations r
                    JOIN knowledge_entities se ON se.id = r.source_entity_id
                    JOIN knowledge_entities te ON te.id = r.target_entity_id
                    WHERE r.run_id = %s
                    """,
                    (self.run_id,),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_all_documents(self) -> list[dict[str, Any]]:
        if self.run_id is None:
            return []
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, source, title, url, query, depth
                    FROM raw_documents WHERE run_id = %s
                    ORDER BY id
                    """,
                    (self.run_id,),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_entity_id_map(self) -> dict[tuple[str, str], int]:
        if self.run_id is None:
            return {}
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, entity_type, name FROM knowledge_entities WHERE run_id = %s",
                    (self.run_id,),
                )
                return {(row[1], row[2].lower()): row[0] for row in cur.fetchall()}

    def claim_unextracted_documents(self, limit: int) -> list[dict[str, Any]]:
        """Atomically claim a batch for extraction (safe for parallel workers)."""
        if self.run_id is None:
            return []
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE raw_documents
                    SET metadata = COALESCE(metadata, '{}'::jsonb) || '{"_claim":"1"}'::jsonb
                    WHERE id IN (
                        SELECT id FROM raw_documents
                        WHERE run_id = %s
                          AND extracted = FALSE
                          AND COALESCE(metadata->>'_claim', '') != '1'
                        ORDER BY id
                        LIMIT %s
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING id, source, external_id, title, content, url, query, depth, metadata
                    """,
                    (self.run_id, limit),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def release_claimed_documents(self, doc_ids: list[int]) -> None:
        if not doc_ids:
            return
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE raw_documents
                    SET metadata = metadata - '_claim'
                    WHERE id = ANY(%s) AND extracted = FALSE
                    """,
                    (doc_ids,),
                )

    def has_unextracted_documents(self) -> bool:
        if self.run_id is None:
            return False
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM raw_documents
                        WHERE run_id = %s AND extracted = FALSE
                    )
                    """,
                    (self.run_id,),
                )
                return bool(cur.fetchone()[0])

    def flush_session_data(self, session_id: str | None = None) -> dict[str, int]:
        """Delete all analyzer DB rows for a session (raw docs, queries, knowledge, runs)."""
        sid = session_id or self.session_id
        if not sid:
            return {}

        counts: dict[str, int] = {}
        with get_connection(self.database_url) as conn:
            with conn.cursor() as cur:
                tables = (
                    ("knowledge_relations", "session_id"),
                    ("knowledge_entities", "session_id"),
                    ("raw_documents", "session_id"),
                    ("search_queries", "session_id"),
                    ("analysis_runs", "session_id"),
                )
                for table, col in tables:
                    cur.execute(f"DELETE FROM {table} WHERE {col} = %s", (sid,))
                    counts[table] = cur.rowcount

        if self.session_id == sid:
            self.run_id = None

        return counts

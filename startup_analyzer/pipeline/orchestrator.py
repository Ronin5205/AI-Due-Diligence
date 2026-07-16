"""Main analysis loop: query → collect → extract → expand (depth 2-4)."""
from __future__ import annotations

import sys
import time
from typing import Any

from config import AnalyzerConfig
from llm import gemini_client
from schemas.analyzer import AnalysisMetadata, EvaluationReport, EvidenceItem, GeminiUsage
from output.report_builder import build_report
from pipeline.collector import Collector
from pipeline.extraction_queue import ExtractionQueue
from pipeline.graph import KnowledgeGraph
from pipeline.knowledge import build_structured_knowledge
from pipeline.query_expansion import expand_queries_for_depth
from pipeline.query_generator import generate_initial_queries
from sources.registry import build_sources
from storage.repository import Repository


class Orchestrator:
    def __init__(self, config: AnalyzerConfig, session: dict[str, Any]):
        self.config = config
        self.session = session
        self.startup = session["startup"]
        self.session_id = session["session_id"]
        self.repo = Repository(config.database_url)
        self.sources = build_sources(config)
        self.enabled_sources = [
            name for name, src in self.sources.items() if src.is_configured()
        ]
        self.collector = Collector(
            self.repo,
            self.sources,
            search_workers=config.search_workers,
        )
        self.graph = KnowledgeGraph(startup_name=self.startup.company_name or self.session_id)
        self.start_time = time.time()

    def _startup_context(self) -> dict[str, Any]:
        profile = self.startup.model_dump()
        return {k: v for k, v in profile.items() if k != "search_seeds" and v not in (None, "")}

    def run(self) -> EvaluationReport:
        if not self.config.database_url:
            raise RuntimeError("DATABASE_URL is required. Set your Supabase Postgres connection string in .env")

        if not self.config.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required.")

        if not self.enabled_sources:
            print("[orchestrator] warning: no configured sources available", file=sys.stderr)

        self.repo.create_run(self.session_id, self.config.max_depth)
        existing_queries: set[str] = set()
        depth_reached = 0

        extraction_queue = ExtractionQueue(
            self.repo,
            self._startup_context(),
            batch_size=self.config.extraction_batch_size,
            workers=self.config.extraction_workers,
        )
        extraction_queue.start()

        try:
            initial = generate_initial_queries(
                self.startup,
                self.enabled_sources,
                self.config.queries_per_source_depth0,
                existing_queries,
            )
            self.repo.insert_queries(initial)
            for q in initial:
                existing_queries.add(q.query.lower())

            for depth in range(self.config.max_depth + 1):
                depth_reached = depth
                print(f"[orchestrator] depth {depth}: collecting (parallel)...", file=sys.stderr)
                new_docs = self.collector.run_pending_parallel(depth=depth)
                print(f"[orchestrator] depth {depth}: collected {new_docs} new documents", file=sys.stderr)

                print(f"[orchestrator] depth {depth}: waiting for extraction queue...", file=sys.stderr)
                extraction_queue.wait_until_drained()

                entities = self.repo.get_all_entities()
                relations = self.repo.get_all_relations()

                if depth >= self.config.max_depth:
                    break

                if new_docs == 0 and depth > 0:
                    print("[orchestrator] no new docs, stopping early", file=sys.stderr)
                    break

                expanded = expand_queries_for_depth(
                    entities=entities,
                    relations=relations,
                    startup_context=self._startup_context(),
                    enabled_sources=self.enabled_sources,
                    depth=depth + 1,
                    existing_queries=existing_queries,
                    limit_per_source=self.config.queries_per_source_depth_n,
                )
                if not expanded:
                    print(
                        f"[orchestrator] no expansion queries at depth {depth + 1}, stopping",
                        file=sys.stderr,
                    )
                    break

                self.repo.insert_queries(expanded)
                for q in expanded:
                    existing_queries.add(q.query.lower())
                    self.graph.mark_searched(q.query)
        finally:
            extraction_queue.wait_until_drained()
            extraction_queue.stop()

        entities = self.repo.get_all_entities()
        relations = self.repo.get_all_relations()
        structured = build_structured_knowledge(entities)
        kg = self.graph.build(entities, relations)
        docs = self.repo.get_all_documents()

        evidence_index = [
            EvidenceItem(
                doc_id=d.get("id"),
                source=d.get("source", ""),
                url=d.get("url", ""),
                title=d.get("title", ""),
                relevance=f"depth {d.get('depth', 0)} query: {d.get('query', '')}",
            )
            for d in docs
        ]

        metadata = AnalysisMetadata(
            depth_reached=depth_reached,
            queries_executed=self.repo.count_queries(),
            documents_collected=self.repo.count_documents(),
            sources_used=sorted(self.collector.sources_used),
            sources_skipped=sorted(self.collector.sources_skipped),
            duration_seconds=round(time.time() - self.start_time, 1),
            gemini_usage=GeminiUsage(**gemini_client.get_gemini_usage()),
        )

        print("[orchestrator] synthesizing evaluation...", file=sys.stderr)
        evaluation = gemini_client.synthesize_evaluation(
            startup_profile=self.startup.model_dump(),
            structured_knowledge=structured,
            knowledge_graph=kg,
            evidence_index=[e.model_dump() for e in evidence_index],
            analysis_metadata=metadata.model_dump(),
        )

        report = build_report(
            session_id=self.session_id,
            startup=self.startup,
            metadata=metadata,
            structured=structured,
            knowledge_graph=kg,
            evidence_index=evidence_index,
            evaluation=evaluation,
        )

        self.repo.finish_run("completed", metadata=metadata.model_dump())
        return report

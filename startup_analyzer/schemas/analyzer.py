"""Pydantic models for the analyzer pipeline and evaluation output."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RawDocument(BaseModel):
    source: str
    external_id: str
    title: str
    content: str
    url: str
    query: str = ""
    depth: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    collected_at: Optional[datetime] = None


class SearchQueryItem(BaseModel):
    query: str
    source: str
    depth: int = 0
    rationale: str = ""


class KnowledgeEntity(BaseModel):
    entity_type: str
    name: str
    description: str = ""
    confidence: float = 0.5
    mention_count: int = 1
    platforms_seen: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)
    evidence_urls: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeRelation(BaseModel):
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relation_type: str
    confidence: float = 0.5
    evidence_urls: list[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    confidence: float = 0.5
    mention_count: int = 1


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    confidence: float = 0.5
    evidence_urls: list[str] = Field(default_factory=list)


class ScoreDetail(BaseModel):
    score: float
    rationale: str = ""
    confidence: float = 0.5


class GeminiUsage(BaseModel):
    calls_made: int = 0
    max_rpm: int = 20
    total_wait_seconds: float = 0.0
    calls_throttled: int = 0


class AnalysisMetadata(BaseModel):
    depth_reached: int = 0
    queries_executed: int = 0
    documents_collected: int = 0
    sources_used: list[str] = Field(default_factory=list)
    sources_skipped: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    gemini_usage: GeminiUsage = Field(default_factory=GeminiUsage)


class EvidenceItem(BaseModel):
    doc_id: Optional[int] = None
    source: str
    url: str
    title: str
    relevance: str = ""
    extracted_entities: list[str] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    session_id: str
    startup_profile: dict[str, Any]
    analysis_metadata: AnalysisMetadata = Field(default_factory=AnalysisMetadata)
    evaluation_scores: dict[str, Any] = Field(default_factory=dict)
    market_gap_analysis: dict[str, Any] = Field(default_factory=dict)
    competitive_landscape: dict[str, Any] = Field(default_factory=dict)
    problem_validation: dict[str, Any] = Field(default_factory=dict)
    success_and_risk_signals: dict[str, Any] = Field(default_factory=dict)
    structured_knowledge: dict[str, list[Any]] = Field(default_factory=dict)
    knowledge_graph: dict[str, list[Any]] = Field(default_factory=lambda: {"nodes": [], "edges": []})
    evidence_index: list[EvidenceItem] = Field(default_factory=list)

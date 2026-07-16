"""Assemble and write the final evaluation JSON report."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from schemas.analyzer import AnalysisMetadata, EvaluationReport, EvidenceItem

_REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def build_report(
    session_id: str,
    startup: Any,
    metadata: AnalysisMetadata,
    structured: dict[str, list[Any]],
    knowledge_graph: dict[str, Any],
    evidence_index: list[EvidenceItem],
    evaluation: dict[str, Any],
) -> EvaluationReport:
    return EvaluationReport(
        session_id=session_id,
        startup_profile=startup.model_dump(),
        analysis_metadata=metadata,
        evaluation_scores=evaluation.get("evaluation_scores", {}),
        market_gap_analysis=evaluation.get("market_gap_analysis", {}),
        competitive_landscape=evaluation.get("competitive_landscape", {}),
        problem_validation=evaluation.get("problem_validation", {}),
        success_and_risk_signals=evaluation.get("success_and_risk_signals", {}),
        structured_knowledge=structured,
        knowledge_graph=knowledge_graph,
        evidence_index=evidence_index,
    )


def write_report(report: EvaluationReport, output_path: str | None = None) -> Path:
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path:
        path = Path(output_path)
        if not path.is_absolute():
            path = Path.cwd() / path
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = _REPORTS_DIR / f"{report.session_id}_{ts}.json"

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
    return path

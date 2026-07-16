"""Gemini client for query generation, extraction, expansion, and evaluation."""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from google import genai
from google.genai import types as genai_types

from llm.rate_limiter import SlidingWindowRateLimiter

_client = None
_rate_limiter: SlidingWindowRateLimiter | None = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    _client = genai.Client(api_key=api_key)
    return _client


def _get_rate_limiter() -> SlidingWindowRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        max_rpm = int(os.environ.get("GEMINI_MAX_RPM", "20"))
        _rate_limiter = SlidingWindowRateLimiter(max_rpm=max_rpm)
    return _rate_limiter


def get_gemini_usage() -> dict[str, Any]:
    return _get_rate_limiter().snapshot().__dict__


def _model_name() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def _generate_with_retry(
    *,
    prompt: str,
    system_instruction: str,
    json_mode: bool = True,
    max_output_tokens: int = 2048,
    temperature: float = 0.1,
    max_retries: int = 2,
):
    limiter = _get_rate_limiter()
    client = _get_client()
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        limiter.acquire()
        try:
            config_kwargs: dict[str, Any] = {
                "system_instruction": system_instruction,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            }
            if json_mode:
                config_kwargs["response_mime_type"] = "application/json"

            return client.models.generate_content(
                model=_model_name(),
                contents=prompt,
                config=genai_types.GenerateContentConfig(**config_kwargs),
            )
        except Exception as e:
            last_error = e
            err = str(e).lower()
            if "429" in err or "rate" in err or "quota" in err:
                backoff = 2 ** attempt * 3
                print(f"[gemini] API 429/quota, backoff {backoff}s", file=sys.stderr)
                time.sleep(backoff)
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("Gemini call failed after retries")


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _repair_truncated_json(text: str) -> str:
    """Best-effort close for JSON truncated mid-stream."""
    trimmed = text.rstrip()
    if trimmed.endswith("}"):
        return trimmed
    # Drop trailing partial key/value and close open structures
    for _ in range(8):
        try:
            json.loads(trimmed + "}")
            return trimmed + "}"
        except json.JSONDecodeError:
            pass
        cut = max(trimmed.rfind("},"), trimmed.rfind("]"))
        if cut == -1:
            break
        trimmed = trimmed[: cut + 1]
    return trimmed + "}"


def _parse_json_loose(text: str) -> dict[str, Any]:
    """Parse Gemini JSON output, tolerating fences, extra trailing text, or truncation."""
    text = _strip_markdown_fences(text)
    if not text:
        return {}

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError as e:
        err = str(e)

        if "Extra data" in err:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text)
            if isinstance(obj, dict):
                return obj

        for candidate in (text, _repair_truncated_json(text)):
            try:
                decoder = json.JSONDecoder()
                obj, _ = decoder.raw_decode(candidate)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue

        raise


def _safe_json_call(
    prompt: str,
    system_instruction: str,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    text = ""
    try:
        response = _generate_with_retry(
            prompt=prompt,
            system_instruction=system_instruction,
            json_mode=True,
            max_output_tokens=max_tokens,
        )
        text = (response.text or "").strip()
        return _parse_json_loose(text)
    except json.JSONDecodeError as e:
        print(f"[gemini] JSON parse error: {e}. Raw: {text[:200]!r}", file=sys.stderr)
        try:
            response = _generate_with_retry(
                prompt=prompt + "\n\nReturn ONE compact JSON object only. No markdown. No trailing text.",
                system_instruction=system_instruction,
                json_mode=True,
                max_output_tokens=min(max_tokens * 2, 8192),
            )
            text = (response.text or "").strip()
            return _parse_json_loose(text)
        except Exception as e2:
            print(f"[gemini] JSON retry failed: {e2}", file=sys.stderr)
            return {}
    except Exception as e:
        print(f"[gemini] call failed: {type(e).__name__}: {e}", file=sys.stderr)
        return {}


_QUERY_SYSTEM = """You generate search queries for startup market research.
Given a startup profile and search seeds, produce platform-specific queries to find:
- market gaps and unmet demand
- competitors and alternatives
- similar startup success/failure signals
- technology adoption and feasibility
- traction and willingness-to-pay proxies

Return JSON:
{
  "queries": [
    {"query": "...", "source": "reddit|hackernews|github|product_hunt|google_trends", "rationale": "..."}
  ]
}

Rules:
- 3-5 queries per enabled source
- Queries must be short (2-8 words), searchable
- Focus on evaluation: market gap, competition, success rate signals
- Do not invent company names not in the profile/seeds
"""


def generate_search_queries(
    startup_profile: dict[str, Any],
    search_seeds: dict[str, Any],
    enabled_sources: list[str],
    depth: int = 0,
    existing_queries: list[str] | None = None,
) -> list[dict[str, str]]:
    prompt = (
        f"Depth: {depth}\n"
        f"Enabled sources: {enabled_sources}\n"
        f"Startup profile: {json.dumps(startup_profile, default=str)}\n"
        f"Search seeds: {json.dumps(search_seeds, default=str)}\n"
        f"Already searched (avoid duplicates): {existing_queries or []}\n\n"
        "Generate search queries for startup due diligence evaluation."
    )
    result = _safe_json_call(prompt, _QUERY_SYSTEM, max_tokens=2048)
    queries = result.get("queries", [])
    cleaned = []
    for q in queries:
        if not isinstance(q, dict):
            continue
        source = str(q.get("source", "")).strip().lower()
        query = str(q.get("query", "")).strip()
        if source in enabled_sources and query:
            cleaned.append({
                "query": query,
                "source": source,
                "rationale": str(q.get("rationale", "")),
            })
    return cleaned


_EXTRACTION_SYSTEM = """Extract structured knowledge from web documents for startup evaluation.

Return ONE JSON object only (no markdown, no commentary after the JSON):
{
  "companies": [{"name": "", "description": "", "confidence": 0.0-1.0, "evidence_snippet": ""}],
  "problems": [{"name": "", "description": "", "confidence": 0.0-1.0, "evidence_snippet": ""}],
  "features": [{"name": "", "description": "", "confidence": 0.0-1.0, "evidence_snippet": ""}],
  "technologies": [{"name": "", "description": "", "confidence": 0.0-1.0, "evidence_snippet": ""}],
  "market_signals": [{"signal": "", "type": "demand|saturation|timing|gap", "confidence": 0.0-1.0, "evidence_snippet": ""}],
  "success_indicators": [{"indicator": "", "confidence": 0.0-1.0, "evidence_snippet": ""}],
  "failure_patterns": [{"pattern": "", "confidence": 0.0-1.0, "evidence_snippet": ""}],
  "relations": [{"source_name": "", "source_type": "", "target_name": "", "target_type": "", "relation_type": "competes_with|solves|uses|mentions_pain|similar_to", "confidence": 0.0-1.0}]
}

Rules:
- Only extract facts supported by the documents
- Max 5 items per array; keep evidence_snippet under 120 chars
- Omit empty arrays entirely
"""


def extract_knowledge_from_documents(
    documents: list[dict[str, Any]],
    startup_context: dict[str, Any],
) -> dict[str, Any]:
    if not documents:
        return {}

    doc_text = []
    for d in documents:
        doc_text.append(
            f"--- DOC id={d.get('id')} source={d.get('source')} url={d.get('url')} ---\n"
            f"Title: {d.get('title', '')}\n"
            f"Content: {(d.get('content') or '')[:1200]}"
        )

    prompt = (
        f"Startup context: {json.dumps(startup_context, default=str)}\n\n"
        f"Documents ({len(documents)}):\n" + "\n\n".join(doc_text) + "\n\n"
        "Extract structured knowledge. Be selective — quality over quantity."
    )
    return _safe_json_call(prompt, _EXTRACTION_SYSTEM, max_tokens=8192)


_EXPANSION_SYSTEM = """You expand search queries based on discovered knowledge for deeper market research (depth 2-4).

Given entities and relations found so far, generate NEW follow-up queries to validate:
- market gaps
- competitor positioning
- success/failure patterns of similar startups
- technology trends

Return JSON:
{
  "queries": [
    {"query": "...", "source": "reddit|hackernews|github|product_hunt|google_trends", "rationale": "..."}
  ]
}

Do not repeat already-searched queries. Max 3 queries per source.
"""


def expand_queries(
    entities: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    startup_context: dict[str, Any],
    enabled_sources: list[str],
    depth: int,
    existing_queries: list[str],
) -> list[dict[str, str]]:
    prompt = (
        f"Depth: {depth}\n"
        f"Enabled sources: {enabled_sources}\n"
        f"Startup: {json.dumps(startup_context, default=str)}\n"
        f"Entities found: {json.dumps(entities[:40], default=str)}\n"
        f"Relations: {json.dumps(relations[:30], default=str)}\n"
        f"Already searched: {existing_queries}\n\n"
        "Generate follow-up search queries."
    )
    result = _safe_json_call(prompt, _EXPANSION_SYSTEM, max_tokens=1536)
    queries = result.get("queries", [])
    cleaned = []
    existing_lower = {q.lower() for q in existing_queries}
    for q in queries:
        if not isinstance(q, dict):
            continue
        source = str(q.get("source", "")).strip().lower()
        query = str(q.get("query", "")).strip()
        if source in enabled_sources and query and query.lower() not in existing_lower:
            cleaned.append({
                "query": query,
                "source": source,
                "rationale": str(q.get("rationale", "")),
            })
    return cleaned


_EVALUATION_SYSTEM = """You synthesize a startup due diligence evaluation from collected market research.

Return JSON with these sections:
{
  "evaluation_scores": {
    "market_gap": {"score": 0-100, "rationale": "...", "confidence": 0.0-1.0},
    "problem_validity": {"score": 0-100, "rationale": "...", "confidence": 0.0-1.0},
    "competition_intensity": {"score": 0-100, "rationale": "...", "confidence": 0.0-1.0},
    "differentiation": {"score": 0-100, "rationale": "...", "confidence": 0.0-1.0},
    "technology_feasibility": {"score": 0-100, "rationale": "...", "confidence": 0.0-1.0},
    "success_likelihood": {"score": 0-100, "rationale": "...", "confidence": 0.0-1.0},
    "overall": {"score": 0-100, "verdict": "high_potential|moderate_risk|low_potential|insufficient_data", "summary": "..."}
  },
  "market_gap_analysis": {
    "gaps_identified": [{"gap": "", "evidence": "", "confidence": 0.0-1.0}],
    "unmet_needs": [],
    "whitespace_opportunities": [],
    "saturation_signals": []
  },
  "competitive_landscape": {
    "direct_competitors": [{"name": "", "strengths": "", "weaknesses": "", "evidence_url": ""}],
    "indirect_alternatives": [],
    "differentiators_claimed": [],
    "differentiators_validated": []
  },
  "problem_validation": {
    "external_pain_evidence": [{"evidence": "", "source_url": "", "confidence": 0.0-1.0}],
    "contradictions_with_founder_claims": [],
    "demand_signals": []
  },
  "success_and_risk_signals": {
    "similar_startup_outcomes": [{"startup": "", "outcome": "", "evidence_url": ""}],
    "traction_patterns": [],
    "failure_patterns": [],
    "key_risks": [{"risk": "", "severity": "low|medium|high", "rationale": ""}]
  }
}

Base scores on evidence, not assumptions. Note contradictions between founder claims and external data.
Cite evidence URLs where available.
"""


def synthesize_evaluation(
    startup_profile: dict[str, Any],
    structured_knowledge: dict[str, Any],
    knowledge_graph: dict[str, Any],
    evidence_index: list[dict[str, Any]],
    analysis_metadata: dict[str, Any],
) -> dict[str, Any]:
    prompt = (
        f"Startup profile: {json.dumps(startup_profile, default=str)}\n"
        f"Structured knowledge: {json.dumps(structured_knowledge, default=str)}\n"
        f"Knowledge graph: {json.dumps(knowledge_graph, default=str)}\n"
        f"Evidence index ({len(evidence_index)} items): {json.dumps(evidence_index[:50], default=str)}\n"
        f"Analysis metadata: {json.dumps(analysis_metadata, default=str)}\n\n"
        "Produce the final due diligence evaluation."
    )
    return _safe_json_call(prompt, _EVALUATION_SYSTEM, max_tokens=6144)

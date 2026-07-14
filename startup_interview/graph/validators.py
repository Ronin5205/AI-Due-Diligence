"""
Deterministic validation and contradiction detection. Pure backend
logic — the LLM's job ends at extraction; everything here is rules.
"""
from __future__ import annotations

import re
from typing import Any

from models.schema import SEARCH_SEED_BUCKETS, SearchSeeds, StartupProfile
from graph import question_bank as qb


def _is_empty(value: Any) -> bool:
    return value in (None, "", [], {})


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _word_overlap_ratio(a: str, b: str) -> float:
    wa = set(_normalize_text(a).split())
    wb = set(_normalize_text(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


# Pairs that suggest a genuine factual conflict (not additive detail)
_MUTUALLY_EXCLUSIVE = (
    ("daily", "rarely"),
    ("daily", "never"),
    ("always", "never"),
    ("b2b", "b2c"),
    ("enterprise", "consumer"),
    ("yes", "no"),
    ("technical", "non-technical"),
    ("non-technical", "technical"),
)


def is_additive_update(old: str, new: str) -> bool:
    """True when new text refines or extends old text rather than conflicting."""
    o = _normalize_text(old)
    n = _normalize_text(new)
    if not o or not n:
        return True
    if o == n:
        return True
    if o in n or n in o:
        return True
    if _word_overlap_ratio(old, new) >= 0.35:
        return True
    return False


def merge_scalar_field(old: str | None, new: str) -> str:
    """
    Merge a new field value into an existing one.
    Prefer enriched combined text when the update adds detail.
    """
    if _is_empty(old):
        return new.strip()
    if _is_empty(new):
        return str(old).strip()

    o = str(old).strip()
    n = new.strip()
    on, nn = _normalize_text(o), _normalize_text(n)

    if on == nn:
        return n if len(n) >= len(o) else o
    if on in nn:
        return n
    if nn in on:
        return o

    if is_additive_update(o, n):
        parts: list[str] = []
        seen: set[str] = set()
        for chunk in re.split(r"[;,\n]\s*", f"{o}; {n}"):
            key = _normalize_text(chunk)
            if key and key not in seen:
                seen.add(key)
                parts.append(chunk.strip())
        return "; ".join(parts)

    return n


def is_true_contradiction(old: str, new: str, field: str = "") -> bool:
    """
    True only when the new value genuinely conflicts with the old value —
    not when it adds detail, examples, or a richer phrasing of the same fact.
    """
    if _is_empty(old) or _is_empty(new):
        return False
    if is_additive_update(str(old), new):
        return False

    o = _normalize_text(str(old))
    n = _normalize_text(new)

    if field == "problem_pain_level":
        try:
            old_num = int(re.search(r"\d+", o).group())  # type: ignore[union-attr]
            new_num = int(re.search(r"\d+", n).group())  # type: ignore[union-attr]
            return old_num != new_num
        except (AttributeError, ValueError):
            pass

    for a, b in _MUTUALLY_EXCLUSIVE:
        if (a in o and b in n) or (b in o and a in n):
            return True

    return False


def merge_extracted_fields(
    startup: StartupProfile,
    extracted: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """
    Merge extracted scalars into the profile dict.
    Returns (merged_data, true_contradiction_messages).
    """
    data = startup.model_dump()
    contradictions: list[str] = []

    for field, value in extracted.items():
        if field not in qb.REQUIRED_FIELDS or not isinstance(value, str):
            data[field] = value
            continue

        old_value = data.get(field)
        if _is_empty(old_value):
            data[field] = value.strip()
            continue

        old_str = str(old_value)
        if is_true_contradiction(old_str, value, field):
            contradictions.append(
                f"{field} was previously '{old_str}', now stated as '{value}'"
            )
            data[field] = value.strip()
        else:
            data[field] = merge_scalar_field(old_str, value)

    return data, contradictions


def compute_missing_fields(startup: StartupProfile, skipped_fields: list[str]) -> list[str]:
    """
    Return fields still needed for interview completion.

    Research categories complete on category minimums — unfilled required/enhanced
    fields in a satisfied category are not missing. Due-diligence fields (no
    category) with tier "required" are always needed until filled.
    """
    missing = []
    categories_met = {cat: qb.category_minimum_met(startup, cat) for cat in qb.RESEARCH_CATEGORIES}

    for field in qb.REQUIRED_FIELDS:
        if field in skipped_fields:
            continue
        if not _is_empty(getattr(startup, field)):
            continue

        tier = qb.FIELD_TIERS.get(field, "required")
        category = qb.FIELD_CATEGORIES.get(field)

        if category is None:
            if tier == "required":
                missing.append(field)
        elif not categories_met.get(category, False):
            missing.append(field)

    return missing


def merge_search_seeds(existing: SearchSeeds, extracted: dict[str, list[str]]) -> SearchSeeds:
    """Merge new entity lists into existing seeds, deduplicating case-insensitively."""
    data = existing.model_dump()
    for bucket in SEARCH_SEED_BUCKETS:
        new_items = extracted.get(bucket, [])
        if not new_items:
            continue
        current = data.get(bucket, [])
        seen = {s.strip().lower() for s in current if isinstance(s, str)}
        for item in new_items:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            if not cleaned:
                continue
            key = cleaned.lower()
            if key not in seen:
                seen.add(key)
                current.append(cleaned)
        data[bucket] = current
    return SearchSeeds(**data)


def detect_contradictions(
    startup: StartupProfile,
    extracted: dict[str, Any],
) -> list[str]:
    """Return only genuine contradictions — additive updates are not flagged."""
    _, contradictions = merge_extracted_fields(startup, extracted)
    return contradictions


def validate_extracted_values(extracted: dict[str, Any]) -> list[str]:
    """Basic sanity checks before the values ever touch StartupProfile."""
    errors = []
    for field, value in extracted.items():
        if value is not None and isinstance(value, str):
            if not value.strip():
                errors.append(f"{field} cannot be empty")
        if field == "problem_pain_level" and value is not None:
            try:
                level = int(str(value).strip())
                if not 1 <= level <= 10:
                    errors.append("problem_pain_level must be between 1 and 10")
            except ValueError:
                pass
    return errors


# Must-have fields — gap-fill questions 16–25 only if these remain empty after core beats
CRITICAL_FIELDS: list[str] = qb.CRITICAL_GAP_FIELDS


def critical_gaps_missing(startup: StartupProfile, skipped_fields: list[str]) -> list[str]:
    missing = set(compute_missing_fields(startup, skipped_fields))
    return [f for f in CRITICAL_FIELDS if f in missing]


def is_interview_complete(
    startup: StartupProfile,
    skipped_fields: list[str],
    questions_asked: int,
    beats_asked: list[str],
) -> bool:
    """Complete after 15 core beats (min), optional gap-fill up to 25, hard cap at 25."""
    if questions_asked >= qb.MAX_QUESTIONS:
        return True
    if questions_asked < qb.MIN_QUESTIONS:
        return False
    if not qb.core_beats_complete(beats_asked):
        return False
    gaps = critical_gaps_missing(startup, skipped_fields)
    if gaps and questions_asked < qb.MAX_QUESTIONS:
        return False
    return True


def format_readiness_report(
    startup: StartupProfile,
    missing_fields: list[str],
    questions_asked: int = 0,
    beats_asked: list[str] | None = None,
) -> str:
    """Human-readable platform readiness snapshot."""
    beats_asked = beats_asked or []
    lines = [
        f"Pitch progress: {questions_asked} questions asked, "
        f"{len(beats_asked)}/{len(qb.CORE_BEAT_IDS)} core beats covered "
        f"(target {qb.MIN_QUESTIONS}–{qb.MAX_QUESTIONS} questions).",
    ]
    scores = qb.get_platform_readiness_report(
        startup, startup.search_seeds, missing_fields
    )
    lines.append("\nSearch platform readiness:")
    for platform, score in scores.items():
        status = "ready" if score >= 0.7 else "needs data"
        lines.append(f"  - {platform}: {score:.0%} ({status})")

    seed_counts = startup.search_seeds.model_dump()
    lines.append("\nSearch seed counts:")
    for bucket, items in seed_counts.items():
        minimum = qb.SEARCH_SEED_MINIMUMS.get(bucket, 0)
        marker = " *" if minimum and len(items) < minimum else ""
        lines.append(f"  - {bucket}: {len(items)}{marker}")

    cat_status = []
    for cat in qb.RESEARCH_CATEGORIES:
        met = qb.category_minimum_met(startup, cat)
        filled = qb._category_filled_count(startup, cat)
        needed = qb.CATEGORY_MINIMUMS[cat]["required"]
        cat_status.append(f"{cat}: {filled}/{needed} {'OK' if met else 'INCOMPLETE'}")
    lines.append("\nResearch categories:")
    lines.extend(f"  - {s}" for s in cat_status)

    return "\n".join(lines)

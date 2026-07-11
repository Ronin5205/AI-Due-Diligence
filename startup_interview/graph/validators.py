"""
Deterministic validation and contradiction detection. Pure backend
logic — the LLM's job ends at extraction; everything here is rules.
"""
from __future__ import annotations

from typing import Any

from models.schema import StartupProfile
from graph.question_bank import REQUIRED_FIELDS


def compute_missing_fields(startup: StartupProfile, skipped_fields: list[str]) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        if field in skipped_fields:
            continue
        value = getattr(startup, field)
        if value in (None, "", [], {}):
            missing.append(field)
    return missing


def detect_contradictions(
    startup: StartupProfile,
    extracted: dict[str, Any],
) -> list[str]:
    """
    Compare newly extracted scalar values against already-known values.
    A contradiction is flagged when a previously-set field is being
    overwritten with a materially different value.
    """
    contradictions = []
    # Since all fields are now flat text scalar fields, we check all of them.
    for field in REQUIRED_FIELDS:
        if field not in extracted:
            continue
        old_value = getattr(startup, field)
        new_value = extracted[field]
        if old_value is None:
            continue
        if isinstance(old_value, str) and isinstance(new_value, str):
            if old_value.strip().lower() != new_value.strip().lower():
                contradictions.append(
                    f"{field} was previously '{old_value}', now stated as '{new_value}'"
                )
    return contradictions


def validate_extracted_values(extracted: dict[str, Any]) -> list[str]:
    """Basic sanity checks before the values ever touch StartupProfile."""
    errors = []
    # Verify that any extracted field value is a non-empty string if provided
    for field, value in extracted.items():
        if value is not None and isinstance(value, str):
            if not value.strip():
                errors.append(f"{field} cannot be empty")
    return errors

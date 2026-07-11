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
    scalar_fields = [
        "company_name", "industry", "founded_year", "stage",
        "target_customers", "problem_statement", "solution",
        "users", "paying_customers", "mrr", "funding_raised",
    ]
    for field in scalar_fields:
        if field not in extracted:
            continue
        old_value = getattr(startup, field)
        new_value = extracted[field]
        if old_value is None:
            continue
        if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
            if old_value != new_value:
                contradictions.append(
                    f"{field} was previously '{old_value}', now stated as '{new_value}'"
                )
        elif isinstance(old_value, str) and isinstance(new_value, str):
            if old_value.strip().lower() != new_value.strip().lower():
                contradictions.append(
                    f"{field} was previously '{old_value}', now stated as '{new_value}'"
                )
    return contradictions


def validate_extracted_values(extracted: dict[str, Any]) -> list[str]:
    """Basic sanity checks before the values ever touch StartupProfile."""
    errors = []
    for money_field in ("mrr", "funding_raised"):
        if money_field in extracted and isinstance(extracted[money_field], (int, float)):
            if extracted[money_field] < 0:
                errors.append(f"{money_field} cannot be negative")
    for int_field in ("users", "paying_customers", "founded_year"):
        if int_field in extracted and isinstance(extracted[int_field], (int, float)):
            if extracted[int_field] < 0:
                errors.append(f"{int_field} cannot be negative")
    if "founded_year" in extracted:
        year = extracted["founded_year"]
        if isinstance(year, (int, float)) and (year < 1900 or year > 2100):
            errors.append("founded_year looks invalid")
    if "paying_customers" in extracted and "users" in extracted:
        if extracted["paying_customers"] > extracted["users"]:
            errors.append("paying_customers cannot exceed total users")
    return errors

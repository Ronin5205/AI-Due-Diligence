"""
Canonical data schema for the Startup Due Diligence Interviewer.

StartupProfile is the single source of truth. Every node in the graph
reads from and writes to an instance of this model — never to free-form
text. The LLM is only ever allowed to produce JSON that validates
against (a partial view of) this schema.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Intent(str, Enum):
    ANSWER = "answer"
    PARTIAL_ANSWER = "partial_answer"
    CLARIFICATION_REQUEST = "clarification_request"
    OFF_TOPIC = "off_topic"
    REFUSAL = "refusal"
    GREETING = "greeting"
    END_INTERVIEW = "end_interview"
    UNKNOWN = "unknown"


class Founder(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    background: Optional[str] = None


class StartupProfile(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    founded_year: Optional[int] = None

    founders: list[Founder] = Field(default_factory=list)

    stage: Optional[str] = None

    target_customers: Optional[str] = None
    problem_statement: Optional[str] = None
    solution: Optional[str] = None

    users: Optional[int] = None
    paying_customers: Optional[int] = None
    mrr: Optional[float] = None

    competitors: list[str] = Field(default_factory=list)

    funding_raised: Optional[float] = None

    @field_validator("mrr", "funding_raised")
    @classmethod
    def non_negative_money(cls, v):
        if v is not None and v < 0:
            raise ValueError("monetary values cannot be negative")
        return v

    @field_validator("users", "paying_customers", "founded_year")
    @classmethod
    def non_negative_int(cls, v):
        if v is not None and v < 0:
            raise ValueError("value cannot be negative")
        return v


# Fields the LLM is allowed to populate via extraction, in the exact
# shape it must return them (flat, scalar-first). Lists are merged by
# the backend, never overwritten blindly, so extraction returns them
# as "additions" rather than replacements.
EXTRACTABLE_FIELDS = [
    "company_name",
    "industry",
    "founded_year",
    "stage",
    "target_customers",
    "problem_statement",
    "solution",
    "users",
    "paying_customers",
    "mrr",
    "funding_raised",
    "competitors",   # list[str] addition
    "founders",      # list[Founder-like dict] addition
]

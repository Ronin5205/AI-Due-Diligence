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


class StartupProfile(BaseModel):
    # 1. Startup Overview
    company_name: Optional[str] = None
    startup_idea: Optional[str] = None
    inspiration: Optional[str] = None

    # 2. Problem Discovery
    problem_statement: Optional[str] = None
    problem_sufferers: Optional[str] = None
    problem_frequency: Optional[str] = None
    unsolved_consequences: Optional[str] = None

    # 3. Customer Understanding
    ideal_customer: Optional[str] = None
    current_solutions: Optional[str] = None
    solutions_inadequate: Optional[str] = None

    # 4. Solution Design
    solution: Optional[str] = None
    how_it_solves: Optional[str] = None
    why_choose_it: Optional[str] = None

    # 5. Founder Fit
    founder_fit: Optional[str] = None
    industry_experience: Optional[str] = None
    founder_skills: Optional[str] = None

    # 6. Competition
    competitors: Optional[str] = None
    alternatives: Optional[str] = None
    why_switch: Optional[str] = None

    # 7. Business Model
    monetization: Optional[str] = None
    paying_customers: Optional[str] = None
    why_pay: Optional[str] = None

    # 8. Execution Plan
    first_version: Optional[str] = None
    required_resources: Optional[str] = None
    biggest_risk: Optional[str] = None


# Fields the LLM is allowed to populate via extraction
EXTRACTABLE_FIELDS = [
    "company_name",
    "startup_idea",
    "inspiration",
    "problem_statement",
    "problem_sufferers",
    "problem_frequency",
    "unsolved_consequences",
    "ideal_customer",
    "current_solutions",
    "solutions_inadequate",
    "solution",
    "how_it_solves",
    "why_choose_it",
    "founder_fit",
    "industry_experience",
    "founder_skills",
    "competitors",
    "alternatives",
    "why_switch",
    "monetization",
    "paying_customers",
    "why_pay",
    "first_version",
    "required_resources",
    "biggest_risk",
]

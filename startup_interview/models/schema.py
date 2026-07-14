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


class SearchSeeds(BaseModel):
    """Entities extracted for recursive search generation."""

    companies: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    job_titles: list[str] = Field(default_factory=list)
    software: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    feature_requests: list[str] = Field(default_factory=list)
    customer_segments: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)


SEARCH_SEED_BUCKETS = list(SearchSeeds.model_fields.keys())


class StartupProfile(BaseModel):
    # 1. Startup Overview
    company_name: Optional[str] = None
    startup_idea: Optional[str] = None
    inspiration: Optional[str] = None

    # 2. Problem
    core_problem: Optional[str] = None
    problem_when: Optional[str] = None
    problem_frequency: Optional[str] = None
    problem_pain_level: Optional[str] = None
    unsolved_consequences: Optional[str] = None

    # 3. Customer
    target_customer: Optional[str] = None
    customer_job_titles: Optional[str] = None
    customer_company_size: Optional[str] = None
    customer_industry: Optional[str] = None
    customer_sub_industry: Optional[str] = None
    customer_technical_expertise: Optional[str] = None

    # 4. Current Workflow
    current_workflow: Optional[str] = None
    manual_steps: Optional[str] = None
    bottlenecks: Optional[str] = None
    time_spent: Optional[str] = None
    workarounds: Optional[str] = None

    # 5. Ecosystem
    competitors: Optional[str] = None
    alternatives: Optional[str] = None
    software_used: Optional[str] = None
    apis_used: Optional[str] = None
    integrations: Optional[str] = None
    frameworks_used: Optional[str] = None
    platforms_used: Optional[str] = None

    # 6. Industry Language
    industry_keywords: Optional[str] = None
    industry_jargon: Optional[str] = None
    industry_acronyms: Optional[str] = None
    technical_terms: Optional[str] = None
    synonyms: Optional[str] = None

    # 7. Customer Vocabulary
    customer_phrases: Optional[str] = None

    # 8. Feature Requests
    desired_features: Optional[str] = None
    missing_capabilities: Optional[str] = None
    biggest_frustrations: Optional[str] = None
    wish_statements: Optional[str] = None

    # 9. Related Technologies
    related_languages: Optional[str] = None
    related_frameworks: Optional[str] = None
    related_databases: Optional[str] = None
    cloud_providers: Optional[str] = None
    protocols: Optional[str] = None
    standards: Optional[str] = None

    # 10. Market Context
    regulations: Optional[str] = None
    compliance_requirements: Optional[str] = None
    industry_standards: Optional[str] = None
    file_formats: Optional[str] = None
    business_processes: Optional[str] = None

    # 11. Solution Design (Due Diligence)
    solution: Optional[str] = None
    how_it_solves: Optional[str] = None
    why_choose_it: Optional[str] = None

    # 12. Founder Fit (Due Diligence)
    founder_fit: Optional[str] = None
    industry_experience: Optional[str] = None
    founder_skills: Optional[str] = None

    # 13. Business Model (Due Diligence)
    why_switch: Optional[str] = None
    monetization: Optional[str] = None
    paying_customers: Optional[str] = None
    why_pay: Optional[str] = None

    # 14. Execution Plan (Due Diligence)
    first_version: Optional[str] = None
    required_resources: Optional[str] = None
    biggest_risk: Optional[str] = None

    # Search seed entities (auto-populated during interview)
    search_seeds: SearchSeeds = Field(default_factory=SearchSeeds)

    @field_validator("problem_pain_level")
    @classmethod
    def validate_pain_level(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        try:
            level = int(v.strip())
        except ValueError:
            return v
        if not 1 <= level <= 10:
            raise ValueError("problem_pain_level must be between 1 and 10")
        return str(level)


# Legacy field names mapped to new names (for session migration)
LEGACY_FIELD_ALIASES: dict[str, str] = {
    "problem_statement": "core_problem",
    "problem_sufferers": "target_customer",
    "ideal_customer": "target_customer",
    "current_solutions": "current_workflow",
    "solutions_inadequate": "missing_capabilities",
}


# Fields the LLM is allowed to populate via extraction
EXTRACTABLE_FIELDS = [
    "company_name",
    "startup_idea",
    "inspiration",
    "core_problem",
    "problem_when",
    "problem_frequency",
    "problem_pain_level",
    "unsolved_consequences",
    "target_customer",
    "customer_job_titles",
    "customer_company_size",
    "customer_industry",
    "customer_sub_industry",
    "customer_technical_expertise",
    "current_workflow",
    "manual_steps",
    "bottlenecks",
    "time_spent",
    "workarounds",
    "competitors",
    "alternatives",
    "software_used",
    "apis_used",
    "integrations",
    "frameworks_used",
    "platforms_used",
    "industry_keywords",
    "industry_jargon",
    "industry_acronyms",
    "technical_terms",
    "synonyms",
    "customer_phrases",
    "desired_features",
    "missing_capabilities",
    "biggest_frustrations",
    "wish_statements",
    "related_languages",
    "related_frameworks",
    "related_databases",
    "cloud_providers",
    "protocols",
    "standards",
    "regulations",
    "compliance_requirements",
    "industry_standards",
    "file_formats",
    "business_processes",
    "solution",
    "how_it_solves",
    "why_choose_it",
    "founder_fit",
    "industry_experience",
    "founder_skills",
    "why_switch",
    "monetization",
    "paying_customers",
    "why_pay",
    "first_version",
    "required_resources",
    "biggest_risk",
]

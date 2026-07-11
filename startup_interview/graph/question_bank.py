"""
Static interview configuration. This is deliberately plain Python data
— the LLM never decides field order or what's required. The backend
owns this completely.
"""

# Order matters: this is the sequence question_selector walks through.
REQUIRED_FIELDS: list[str] = [
    "company_name",
    "industry",
    "founded_year",
    "stage",
    "problem_statement",
    "solution",
    "target_customers",
    "users",
    "paying_customers",
    "mrr",
    "competitors",
    "funding_raised",
]

FIELD_DESCRIPTIONS: dict[str, str] = {
    "company_name": "The official name of the company/startup.",
    "industry": "The industry or market category the startup operates in.",
    "founded_year": "The year the company was founded.",
    "stage": "The current funding/product stage (e.g. pre-seed, seed, Series A, bootstrapped).",
    "problem_statement": "The core problem the startup is solving.",
    "solution": "How the startup solves that problem — the product itself.",
    "target_customers": "Who the primary customers are and what defines them.",
    "users": "Total number of users on the platform (paying or not).",
    "paying_customers": "Number of customers currently paying.",
    "mrr": "Current monthly recurring revenue, in USD.",
    "competitors": "Key competitors in the space.",
    "funding_raised": "Total funding raised to date, in USD.",
}

# Used only if the LLM is unavailable or returns an empty string —
# guarantees the interview can never stall.
FALLBACK_QUESTIONS: dict[str, str] = {
    "company_name": "What is the name of your company?",
    "industry": "What industry or market are you operating in?",
    "founded_year": "What year was the company founded?",
    "stage": "What stage is the company at right now (pre-seed, seed, Series A, etc.)?",
    "problem_statement": "What problem are you solving for your customers?",
    "solution": "How does your product solve that problem?",
    "target_customers": "Who are your primary customers, and what characteristics define them?",
    "users": "How many total users do you currently have?",
    "paying_customers": "How many paying customers do you currently have?",
    "mrr": "What is your current monthly recurring revenue (MRR)?",
    "competitors": "Who are your main competitors?",
    "funding_raised": "How much funding have you raised to date?",
}


def find_next_missing_field(missing_fields: list[str]) -> str | None:
    """Return the next field to ask about, honoring REQUIRED_FIELDS order."""
    for field in REQUIRED_FIELDS:
        if field in missing_fields:
            return field
    return None

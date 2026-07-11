"""
Static interview configuration. This is deliberately plain Python data
— the LLM never decides field order or what's required. The backend
owns this completely.
"""

# Group questions by section for modularity and ease of expansion
SECTIONS: list[dict] = [
    {
        "id": "overview",
        "name": "Startup Overview",
        "questions": {
            "company_name": {
                "desc": "The name of the startup.",
                "fallback": "What is the name of your startup?",
            },
            "startup_idea": {
                "desc": "A one-sentence description of the startup idea.",
                "fallback": "Describe your startup idea in one sentence.",
            },
            "inspiration": {
                "desc": "The inspiration behind working on this problem.",
                "fallback": "What inspired you to work on this problem?",
            },
        }
    },
    {
        "id": "problem",
        "name": "Problem Discovery",
        "questions": {
            "problem_statement": {
                "desc": "The specific problem being solved.",
                "fallback": "What specific problem are you solving?",
            },
            "problem_sufferers": {
                "desc": "Who experiences this problem.",
                "fallback": "Who experiences this problem?",
            },
            "problem_frequency": {
                "desc": "How frequently this problem occurs.",
                "fallback": "How frequently does it occur?",
            },
            "unsolved_consequences": {
                "desc": "What happens if this problem remains unsolved.",
                "fallback": "What happens if the problem remains unsolved?",
            },
        }
    },
    {
        "id": "customer",
        "name": "Customer Understanding",
        "questions": {
            "ideal_customer": {
                "desc": "The ideal customer for the solution.",
                "fallback": "Who is your ideal customer?",
            },
            "current_solutions": {
                "desc": "How the target customers currently solve this problem.",
                "fallback": "How do they currently solve this problem?",
            },
            "solutions_inadequate": {
                "desc": "Why current solutions are inadequate.",
                "fallback": "Why are current solutions inadequate?",
            },
        }
    },
    {
        "id": "solution_design",
        "name": "Solution Design",
        "questions": {
            "solution": {
                "desc": "The proposed solution.",
                "fallback": "What solution are you proposing?",
            },
            "how_it_solves": {
                "desc": "How the proposed solution solves the problem.",
                "fallback": "How does it solve the problem?",
            },
            "why_choose_it": {
                "desc": "Why customers would choose this proposed solution.",
                "fallback": "Why would customers choose it?",
            },
        }
    },
    {
        "id": "founder_fit",
        "name": "Founder Fit",
        "questions": {
            "founder_fit": {
                "desc": "Why the founder/founders are the right people to solve this problem.",
                "fallback": "Why are you the right person to solve this problem?",
            },
            "industry_experience": {
                "desc": "The founder's experience working in this industry.",
                "fallback": "Have you worked in this industry before?",
            },
            "founder_skills": {
                "desc": "Relevant skills or experience of the founder/founders.",
                "fallback": "What relevant skills or experience do you have?",
            },
        }
    },
    {
        "id": "competition",
        "name": "Competition",
        "questions": {
            "competitors": {
                "desc": "Key competitors in the space.",
                "fallback": "Who are your competitors?",
            },
            "alternatives": {
                "desc": "The alternatives that exist today.",
                "fallback": "What alternatives exist today?",
            },
            "why_switch": {
                "desc": "Why customers would switch to this proposed solution.",
                "fallback": "Why would customers switch?",
            },
        }
    },
    {
        "id": "business_model",
        "name": "Business Model",
        "questions": {
            "monetization": {
                "desc": "How the startup plans to make money.",
                "fallback": "How do you plan to make money?",
            },
            "paying_customers": {
                "desc": "Who will pay for the solution.",
                "fallback": "Who will pay?",
            },
            "why_pay": {
                "desc": "Why those customers would pay for the solution.",
                "fallback": "Why would they pay?",
            },
        }
    },
    {
        "id": "execution_plan",
        "name": "Execution Plan",
        "questions": {
            "first_version": {
                "desc": "The first version (MVP) planned to build.",
                "fallback": "What is the first version you plan to build?",
            },
            "required_resources": {
                "desc": "The resources needed to execute the plan.",
                "fallback": "What resources do you need?",
            },
            "biggest_risk": {
                "desc": "The biggest risk facing the startup's execution.",
                "fallback": "What is the biggest risk?",
            },
        }
    },
]

# Dynamically construct REQUIRED_FIELDS, FIELD_DESCRIPTIONS, and FALLBACK_QUESTIONS
REQUIRED_FIELDS: list[str] = []
FIELD_DESCRIPTIONS: dict[str, str] = {}
FALLBACK_QUESTIONS: dict[str, str] = {}

for sec in SECTIONS:
    for field, info in sec["questions"].items():
        REQUIRED_FIELDS.append(field)
        FIELD_DESCRIPTIONS[field] = info["desc"]
        FALLBACK_QUESTIONS[field] = info["fallback"]


def find_next_missing_field(missing_fields: list[str]) -> str | None:
    """Return the next field to ask about, honoring REQUIRED_FIELDS order."""
    for field in REQUIRED_FIELDS:
        if field in missing_fields:
            return field
    return None

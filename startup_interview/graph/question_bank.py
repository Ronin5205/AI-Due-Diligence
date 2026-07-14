"""
Static interview configuration. This is deliberately plain Python data
— the LLM never decides field order or what's required. The backend
owns this completely.

Fields are organized into **15 compound pitch beats** (one question each, 15–25 total).
Each beat targets multiple fields; extraction pulls every fact from rich answers.
Question selection is beat-driven with optional gap-fill up to 25 questions.
"""
from __future__ import annotations

from typing import Any

from models.schema import SearchSeeds, StartupProfile

SEARCH_PLATFORMS = [
    "reddit",
    "hackernews",
    "github",
    "product_hunt",
    "google_trends",
]

# Group questions by section for modularity and ease of expansion
SECTIONS: list[dict[str, Any]] = [
    {
        "id": "overview",
        "name": "Startup Overview",
        "category": None,
        "questions": {
            "company_name": {
                "desc": "The name of the startup.",
                "fallback": "What is the name of your startup?",
                "tier": "required",
                "search_platforms": [],
            },
            "startup_idea": {
                "desc": "A one-sentence description of the startup idea.",
                "fallback": "Describe your startup idea in one sentence.",
                "tier": "required",
                "search_platforms": [],
            },
            "inspiration": {
                "desc": "The inspiration behind working on this problem.",
                "fallback": "What inspired you to work on this problem?",
                "tier": "enhanced",
                "search_platforms": ["reddit", "hackernews"],
            },
        },
    },
    {
        "id": "problem",
        "name": "Problem",
        "category": "problem",
        "questions": {
            "core_problem": {
                "desc": "The core problem being solved.",
                "fallback": "What is the core problem you are solving?",
                "tier": "required",
                "search_platforms": ["reddit", "hackernews", "google_trends"],
            },
            "problem_when": {
                "desc": "When this problem occurs in the user's workflow.",
                "fallback": "When does this problem typically occur?",
                "tier": "required",
                "search_platforms": ["reddit", "hackernews"],
            },
            "problem_frequency": {
                "desc": "How frequently this problem occurs.",
                "fallback": "How often does it occur?",
                "tier": "required",
                "search_platforms": ["reddit", "google_trends"],
            },
            "problem_pain_level": {
                "desc": "How painful the problem is on a scale of 1-10.",
                "fallback": "On a scale of 1-10, how painful is this problem?",
                "tier": "required",
                "search_platforms": ["reddit", "product_hunt"],
            },
            "unsolved_consequences": {
                "desc": "What happens if this problem remains unsolved.",
                "fallback": "What happens if the problem remains unsolved?",
                "tier": "required",
                "search_platforms": ["reddit", "hackernews"],
            },
        },
    },
    {
        "id": "customer",
        "name": "Customer",
        "category": "customer",
        "questions": {
            "target_customer": {
                "desc": "The target customer segment.",
                "fallback": "Who is your target customer?",
                "tier": "required",
                "search_platforms": ["reddit", "product_hunt", "google_trends"],
            },
            "customer_job_titles": {
                "desc": "Job titles of people who experience this problem.",
                "fallback": "What job titles experience this problem?",
                "tier": "required",
                "search_platforms": ["reddit", "hackernews", "google_trends"],
            },
            "customer_company_size": {
                "desc": "Typical company size of target customers.",
                "fallback": "What company size do your target customers typically have?",
                "tier": "required",
                "search_platforms": ["product_hunt", "google_trends"],
            },
            "customer_industry": {
                "desc": "Primary industry of target customers.",
                "fallback": "What industry are your target customers in?",
                "tier": "required",
                "search_platforms": ["reddit", "google_trends"],
            },
            "customer_sub_industry": {
                "desc": "Sub-industry or niche within the primary industry.",
                "fallback": "Is there a specific sub-industry or niche?",
                "tier": "enhanced",
                "search_platforms": ["google_trends"],
            },
            "customer_technical_expertise": {
                "desc": "Technical expertise level of target customers.",
                "fallback": "How technically skilled are your target customers?",
                "tier": "enhanced",
                "search_platforms": ["hackernews", "github"],
            },
        },
    },
    {
        "id": "current_workflow",
        "name": "Current Workflow",
        "category": "current_workflow",
        "questions": {
            "current_workflow": {
                "desc": "How the problem is solved today end-to-end.",
                "fallback": "How do people solve this problem today?",
                "tier": "required",
                "search_platforms": ["reddit", "hackernews"],
            },
            "manual_steps": {
                "desc": "Manual steps in the current workflow.",
                "fallback": "What manual steps are involved in the current process?",
                "tier": "required",
                "search_platforms": ["reddit", "hackernews"],
            },
            "bottlenecks": {
                "desc": "Bottlenecks in the current workflow.",
                "fallback": "Where are the biggest bottlenecks?",
                "tier": "required",
                "search_platforms": ["reddit", "hackernews"],
            },
            "time_spent": {
                "desc": "Time spent on the current workflow.",
                "fallback": "How much time does the current process take?",
                "tier": "enhanced",
                "search_platforms": ["reddit"],
            },
            "workarounds": {
                "desc": "Workarounds people use today.",
                "fallback": "What workarounds do people use?",
                "tier": "enhanced",
                "search_platforms": ["reddit", "hackernews"],
            },
        },
    },
    {
        "id": "ecosystem",
        "name": "Existing Ecosystem",
        "category": "ecosystem",
        "questions": {
            "competitors": {
                "desc": "Key competitors in the space.",
                "fallback": "Who are your main competitors?",
                "tier": "required",
                "search_platforms": ["product_hunt", "google_trends"],
            },
            "alternatives": {
                "desc": "Non-software alternatives people use today.",
                "fallback": "What alternatives exist today (including non-software)?",
                "tier": "required",
                "search_platforms": ["reddit", "product_hunt"],
            },
            "software_used": {
                "desc": "Software currently used to address this problem.",
                "fallback": "What software do people currently use for this?",
                "tier": "required",
                "search_platforms": ["github", "product_hunt"],
            },
            "apis_used": {
                "desc": "APIs commonly used in this space.",
                "fallback": "What APIs are commonly used in this workflow?",
                "tier": "enhanced",
                "search_platforms": ["github", "hackernews"],
            },
            "integrations": {
                "desc": "Integrations people need or use.",
                "fallback": "What integrations are important in this space?",
                "tier": "enhanced",
                "search_platforms": ["github", "product_hunt"],
            },
            "frameworks_used": {
                "desc": "Frameworks commonly used in this space.",
                "fallback": "What frameworks are commonly used?",
                "tier": "enhanced",
                "search_platforms": ["github"],
            },
            "platforms_used": {
                "desc": "Platforms (cloud, SaaS, etc.) used in this space.",
                "fallback": "What platforms do people use in this workflow?",
                "tier": "enhanced",
                "search_platforms": ["github", "product_hunt"],
            },
        },
    },
    {
        "id": "industry_language",
        "name": "Industry Language",
        "category": "industry_language",
        "questions": {
            "industry_keywords": {
                "desc": "Keywords used in this industry.",
                "fallback": "What keywords are commonly used in this industry?",
                "tier": "required",
                "search_platforms": ["google_trends"],
            },
            "industry_jargon": {
                "desc": "Industry-specific jargon.",
                "fallback": "What jargon do people in this industry use?",
                "tier": "required",
                "search_platforms": ["reddit", "google_trends"],
            },
            "industry_acronyms": {
                "desc": "Acronyms common in this industry.",
                "fallback": "What acronyms are common in this space?",
                "tier": "enhanced",
                "search_platforms": ["google_trends", "hackernews"],
            },
            "technical_terms": {
                "desc": "Technical terms relevant to this problem.",
                "fallback": "What technical terms are relevant to this problem?",
                "tier": "required",
                "search_platforms": ["github", "hackernews", "google_trends"],
            },
            "synonyms": {
                "desc": "Synonyms for the problem or solution.",
                "fallback": "What other words or phrases describe this same problem?",
                "tier": "enhanced",
                "search_platforms": ["google_trends"],
            },
        },
    },
    {
        "id": "customer_vocabulary",
        "name": "Customer Vocabulary",
        "category": "customer_vocabulary",
        "questions": {
            "customer_phrases": {
                "desc": "Exact phrases users would search or say (e.g. 'inventory reconciliation', 'API drift').",
                "fallback": (
                    "What exact phrases would your users type into Google or say out loud? "
                    "For example: 'keeping frontend in sync', 'manual invoice processing', 'API drift'."
                ),
                "tier": "required",
                "search_platforms": ["reddit", "hackernews", "google_trends"],
            },
        },
    },
    {
        "id": "feature_requests",
        "name": "Feature Requests",
        "category": "feature_requests",
        "questions": {
            "desired_features": {
                "desc": "Features users wish existed.",
                "fallback": "What features do users wish existed?",
                "tier": "required",
                "search_platforms": ["reddit", "product_hunt"],
            },
            "missing_capabilities": {
                "desc": "Capabilities missing from current solutions.",
                "fallback": "What capabilities are missing from current solutions?",
                "tier": "required",
                "search_platforms": ["reddit", "hackernews", "product_hunt"],
            },
            "biggest_frustrations": {
                "desc": "Biggest frustrations with current solutions.",
                "fallback": "What are the biggest frustrations with current solutions?",
                "tier": "required",
                "search_platforms": ["reddit", "hackernews"],
            },
            "wish_statements": {
                "desc": "I wish... statements users make.",
                "fallback": "What 'I wish...' statements do users make about this problem?",
                "tier": "enhanced",
                "search_platforms": ["reddit", "hackernews"],
            },
        },
    },
    {
        "id": "related_technologies",
        "name": "Related Technologies",
        "category": "related_technologies",
        "questions": {
            "related_languages": {
                "desc": "Programming languages relevant to this space.",
                "fallback": "What programming languages are relevant?",
                "tier": "required",
                "search_platforms": ["github"],
            },
            "related_frameworks": {
                "desc": "Frameworks relevant to this space.",
                "fallback": "What frameworks are relevant to this problem?",
                "tier": "required",
                "search_platforms": ["github", "hackernews"],
            },
            "related_databases": {
                "desc": "Databases commonly used in this space.",
                "fallback": "What databases are commonly used?",
                "tier": "enhanced",
                "search_platforms": ["github"],
            },
            "cloud_providers": {
                "desc": "Cloud providers used in this space.",
                "fallback": "What cloud providers are used in this workflow?",
                "tier": "enhanced",
                "search_platforms": ["github", "hackernews"],
            },
            "protocols": {
                "desc": "Protocols relevant to this space.",
                "fallback": "What protocols are relevant (HTTP, gRPC, MQTT, etc.)?",
                "tier": "enhanced",
                "search_platforms": ["github", "hackernews"],
            },
            "standards": {
                "desc": "Standards relevant to this space.",
                "fallback": "What standards apply in this space?",
                "tier": "enhanced",
                "search_platforms": ["github"],
            },
        },
    },
    {
        "id": "market_context",
        "name": "Market Context",
        "category": "market_context",
        "questions": {
            "regulations": {
                "desc": "Regulations affecting this market.",
                "fallback": "What regulations affect this market?",
                "tier": "required",
                "search_platforms": ["reddit", "google_trends"],
            },
            "compliance_requirements": {
                "desc": "Compliance requirements in this space.",
                "fallback": "What compliance requirements apply (SOC2, HIPAA, GDPR, etc.)?",
                "tier": "required",
                "search_platforms": ["reddit", "hackernews"],
            },
            "industry_standards": {
                "desc": "Industry standards buyers expect.",
                "fallback": "What industry standards do buyers expect?",
                "tier": "enhanced",
                "search_platforms": ["google_trends"],
            },
            "file_formats": {
                "desc": "File formats involved in this workflow.",
                "fallback": "What file formats are involved (CSV, PDF, JSON, etc.)?",
                "tier": "enhanced",
                "search_platforms": ["github"],
            },
            "business_processes": {
                "desc": "Business processes this problem touches.",
                "fallback": "What business processes does this problem touch?",
                "tier": "enhanced",
                "search_platforms": ["reddit", "google_trends"],
            },
        },
    },
    {
        "id": "solution_design",
        "name": "Solution Design",
        "category": None,
        "questions": {
            "solution": {
                "desc": "The proposed solution.",
                "fallback": "What solution are you proposing?",
                "tier": "required",
                "search_platforms": [],
            },
            "how_it_solves": {
                "desc": "How the proposed solution solves the problem.",
                "fallback": "How does it solve the problem?",
                "tier": "required",
                "search_platforms": [],
            },
            "why_choose_it": {
                "desc": "Why customers would choose this proposed solution.",
                "fallback": "Why would customers choose it?",
                "tier": "required",
                "search_platforms": [],
            },
        },
    },
    {
        "id": "founder_fit",
        "name": "Founder Fit",
        "category": None,
        "questions": {
            "founder_fit": {
                "desc": "Why the founder/founders are the right people to solve this problem.",
                "fallback": "Why are you the right person to solve this problem?",
                "tier": "required",
                "search_platforms": [],
            },
            "industry_experience": {
                "desc": "The founder's experience working in this industry.",
                "fallback": "Have you worked in this industry before?",
                "tier": "required",
                "search_platforms": [],
            },
            "founder_skills": {
                "desc": "Relevant skills or experience of the founder/founders.",
                "fallback": "What relevant skills or experience do you have?",
                "tier": "required",
                "search_platforms": [],
            },
        },
    },
    {
        "id": "business_model",
        "name": "Business Model",
        "category": None,
        "questions": {
            "why_switch": {
                "desc": "Why customers would switch to this proposed solution.",
                "fallback": "Why would customers switch from current solutions?",
                "tier": "required",
                "search_platforms": ["product_hunt"],
            },
            "monetization": {
                "desc": "How the startup plans to make money.",
                "fallback": "How do you plan to make money?",
                "tier": "required",
                "search_platforms": [],
            },
            "paying_customers": {
                "desc": "Who will pay for the solution.",
                "fallback": "Who will pay?",
                "tier": "required",
                "search_platforms": [],
            },
            "why_pay": {
                "desc": "Why those customers would pay for the solution.",
                "fallback": "Why would they pay?",
                "tier": "required",
                "search_platforms": [],
            },
        },
    },
    {
        "id": "execution_plan",
        "name": "Execution Plan",
        "category": None,
        "questions": {
            "first_version": {
                "desc": "The first version (MVP) planned to build.",
                "fallback": "What is the first version you plan to build?",
                "tier": "required",
                "search_platforms": [],
            },
            "required_resources": {
                "desc": "The resources needed to execute the plan.",
                "fallback": "What resources do you need?",
                "tier": "required",
                "search_platforms": [],
            },
            "biggest_risk": {
                "desc": "The biggest risk facing the startup's execution.",
                "fallback": "What is the biggest risk?",
                "tier": "required",
                "search_platforms": [],
            },
        },
    },
]

# Dynamically construct lookup tables from SECTIONS
REQUIRED_FIELDS: list[str] = []
FIELD_DESCRIPTIONS: dict[str, str] = {}
FALLBACK_QUESTIONS: dict[str, str] = {}
FIELD_TIERS: dict[str, str] = {}
FIELD_SEARCH_PLATFORMS: dict[str, list[str]] = {}
FIELD_CATEGORIES: dict[str, str | None] = {}
FIELD_ORDER: dict[str, int] = {}

_order = 0
for sec in SECTIONS:
    category = sec.get("category")
    for field, info in sec["questions"].items():
        REQUIRED_FIELDS.append(field)
        FIELD_DESCRIPTIONS[field] = info["desc"]
        FALLBACK_QUESTIONS[field] = info["fallback"]
        FIELD_TIERS[field] = info["tier"]
        FIELD_SEARCH_PLATFORMS[field] = info.get("search_platforms", [])
        FIELD_CATEGORIES[field] = category
        FIELD_ORDER[field] = _order
        _order += 1

# Pitch-oriented phrasing (founder-facing). Internal field IDs unchanged.
PITCH_DESCRIPTIONS: dict[str, str] = {
    "company_name": "The startup's name — their opening intro.",
    "startup_idea": "The one-line hook — what they're building in plain English.",
    "inspiration": "The personal moment or story that made them start.",
    "core_problem": "The pain they're obsessed with solving — make it vivid.",
    "problem_when": "When in the day/workflow this pain hits hardest.",
    "problem_frequency": "How often customers feel this — daily annoyance vs rare crisis.",
    "problem_pain_level": "How much this hurts on a 1–10 — their gut feel is fine.",
    "unsolved_consequences": "What goes wrong if nobody fixes this — real stakes.",
    "target_customer": "The specific person they built this for — almost a character.",
    "customer_job_titles": "Who feels this pain at work — titles or roles.",
    "customer_company_size": "Startup, SMB, enterprise — where their first wins are.",
    "customer_industry": "What world their customer lives in.",
    "customer_sub_industry": "Any niche within that industry they dominate first.",
    "customer_technical_expertise": "How technical their buyer/user is.",
    "current_workflow": "The messy status quo before their product exists.",
    "manual_steps": "The tedious steps people suffer through today.",
    "bottlenecks": "Where the current process breaks down or slows to a crawl.",
    "time_spent": "How much time people waste on this today.",
    "workarounds": "The hacks and duct-tape solutions people use now.",
    "competitors": "Who else plays in this space — direct or indirect.",
    "alternatives": "What people do if they don't use software at all.",
    "software_used": "Tools customers already pay for or hack together.",
    "apis_used": "APIs or services woven into the current stack.",
    "integrations": "What their product needs to plug into.",
    "frameworks_used": "Tech stack their users or buyers already live in.",
    "platforms_used": "Cloud/SaaS platforms in the workflow.",
    "industry_keywords": "Words insiders use — the language of the tribe.",
    "industry_jargon": "Insider slang their customers actually say.",
    "industry_acronyms": "Acronyms thrown around in this space.",
    "technical_terms": "Technical words their users would recognize.",
    "synonyms": "Other ways people describe the same problem.",
    "customer_phrases": "Exact quotes — how users complain or search for help.",
    "desired_features": "What users beg for that nothing delivers yet.",
    "missing_capabilities": "Gaps in existing tools your founder sees clearly.",
    "biggest_frustrations": "What makes users want to throw their laptop.",
    "wish_statements": "Real 'I wish...' moments they've heard from users.",
    "related_languages": "Languages that show up in this problem space.",
    "related_frameworks": "Frameworks builders in this space reach for.",
    "related_databases": "Data stores involved in this workflow.",
    "cloud_providers": "Where this kind of product usually runs.",
    "protocols": "Protocols that matter (HTTP, gRPC, webhooks, etc.).",
    "standards": "Standards or specs buyers care about.",
    "regulations": "Rules of the road in this market.",
    "compliance_requirements": "Compliance that gates deals (SOC2, HIPAA, etc.).",
    "industry_standards": "Expectations buyers have — table stakes.",
    "file_formats": "File types that flow through the workflow.",
    "business_processes": "Business processes this touches (procurement, close, etc.).",
    "solution": "Their product — the hero of the pitch.",
    "how_it_solves": "The 'aha' — how it actually fixes the pain.",
    "why_choose_it": "Why someone picks them over the status quo.",
    "founder_fit": "Why they're the one to build this — founder-market fit story.",
    "industry_experience": "Their history in this world.",
    "founder_skills": "Skills or unfair advantages they bring.",
    "why_switch": "The switching story — why customers leave incumbents.",
    "monetization": "How they make money — pricing model, who pays.",
    "paying_customers": "Who signs the check.",
    "why_pay": "The ROI or urgency that justifies budget.",
    "first_version": "What they're shipping first — the wedge.",
    "required_resources": "What they need to get there.",
    "biggest_risk": "What keeps them up at night.",
}

PITCH_FALLBACKS: dict[str, str] = {
    "company_name": "Let's start at the top — what's your startup called?",
    "startup_idea": "Give me the one-liner. What are you building?",
    "inspiration": "What happened that made you drop everything to work on this?",
    "core_problem": "What's the problem you're going after — the one that won't leave you alone?",
    "problem_when": "When does this pain hit your users hardest — mid-project, end of month, always?",
    "problem_frequency": "How often are your users running into this — daily grind or occasional fire drill?",
    "problem_pain_level": "Gut check — on a scale of 1 to 10, how much does this hurt for them?",
    "unsolved_consequences": "If nobody fixes this, what actually breaks for them?",
    "target_customer": "Picture your first true believer — who are they?",
    "customer_job_titles": "Whose desk does this land on — what's their role?",
    "customer_company_size": "Are you starting with scrappy startups, mid-market, or enterprise?",
    "customer_industry": "What industry are they in?",
    "customer_sub_industry": "Any specific niche you're wedge-ing into first?",
    "customer_technical_expertise": "How technical is your buyer — engineer, ops person, non-technical founder?",
    "current_workflow": "Walk me through how people handle this today, before your product exists.",
    "manual_steps": "What's the most tedious part of that process — the part everyone hates?",
    "bottlenecks": "Where does everything slow down or break?",
    "time_spent": "Roughly how much time does this eat per week?",
    "workarounds": "What hacks or duct-tape fixes do people use in the meantime?",
    "competitors": "Who else is going after this — who do you run into in deals?",
    "alternatives": "If they don't use a product like yours, what do they do instead?",
    "software_used": "What tools are they already paying for in this workflow?",
    "apis_used": "Any APIs or services that are part of the stack today?",
    "integrations": "What does your product need to connect to on day one?",
    "frameworks_used": "What tech do your users already build with?",
    "platforms_used": "AWS, Salesforce, Shopify — what platforms show up?",
    "industry_keywords": "What's the vocabulary insiders use when they talk about this space?",
    "industry_jargon": "Any slang or shorthand your customers throw around?",
    "industry_acronyms": "What acronyms does everyone in this space know?",
    "technical_terms": "What technical terms would your user recognize instantly?",
    "synonyms": "What else do people call this same problem?",
    "customer_phrases": (
        "When your users vent about this, what do they actually say — "
        "like a Slack message or a Google search? Things like 'API drift' or "
        "'manual invoice processing'."
    ),
    "desired_features": "What do users keep asking for that nothing does well?",
    "missing_capabilities": "What's missing from the tools out there today?",
    "biggest_frustrations": "What makes your users want to scream at their screen?",
    "wish_statements": "What's a real 'I wish...' you've heard from a user?",
    "related_languages": "What languages show up most in this problem space?",
    "related_frameworks": "What frameworks do builders here reach for?",
    "related_databases": "What databases usually sit behind this kind of workflow?",
    "cloud_providers": "Where does this kind of product typically run?",
    "protocols": "Any protocols that matter here — webhooks, gRPC, MQTT?",
    "standards": "Are there standards or specs buyers expect you to support?",
    "regulations": "Any regulations shaping this market?",
    "compliance_requirements": "SOC2, HIPAA, GDPR — what compliance gates deals?",
    "industry_standards": "What do buyers expect as table stakes?",
    "file_formats": "What file types flow through this workflow — CSV, PDF, JSON?",
    "business_processes": "Which business processes does this touch — close, onboarding, procurement?",
    "solution": "Alright — show me the product. What are you building to fix this?",
    "how_it_solves": "What's the magic moment — how does your thing actually solve it?",
    "why_choose_it": "Why would someone pick you over what they're using today?",
    "founder_fit": "Why are you the right person to build this?",
    "industry_experience": "Have you lived in this industry — or felt this pain yourself?",
    "founder_skills": "What's your unfair advantage — tech, domain, network?",
    "why_switch": "What gets someone to actually switch — not just nod along?",
    "monetization": "How do you make money — and what's the model?",
    "paying_customers": "Who pulls out the credit card?",
    "why_pay": "Why is this worth budget — what's the ROI or urgency?",
    "first_version": "What's the first thing you're shipping — your wedge?",
    "required_resources": "What do you need to pull this off — team, capital, time?",
    "biggest_risk": "What could kill this — what's your biggest worry?",
}

FIELD_PITCH_HOOKS: dict[str, str] = {
    "company_name": "Open the pitch — let them introduce themselves.",
    "startup_idea": "The elevator pitch beat.",
    "inspiration": "Origin story energy.",
    "core_problem": "Dig into the pain that drives everything.",
    "problem_when": "Make the problem concrete in their user's day.",
    "problem_frequency": "Show this isn't a one-off annoyance.",
    "problem_pain_level": "Quantify the urgency.",
    "unsolved_consequences": "Raise the stakes.",
    "target_customer": "Paint the buyer — get specific.",
    "customer_job_titles": "Name the person who feels this.",
    "customer_company_size": "Anchor the beachhead segment.",
    "customer_industry": "Place them in a world.",
    "customer_sub_industry": "Sharpen the wedge.",
    "customer_technical_expertise": "Understand the buyer's sophistication.",
    "current_workflow": "The 'before' picture — status quo pain.",
    "manual_steps": "Where humans are still doing robot work.",
    "bottlenecks": "Find the breaking point.",
    "time_spent": "Make the cost tangible.",
    "workarounds": "Show demand through improvisation.",
    "competitors": "Competitive landscape — who else is pitching this?",
    "alternatives": "The real incumbent might not be software.",
    "software_used": "What's already on their stack.",
    "apis_used": "Technical plumbing in the workflow.",
    "integrations": "What they must plug into.",
    "frameworks_used": "Meet users where they build.",
    "platforms_used": "The platforms in the story.",
    "industry_keywords": "Learn how insiders talk.",
    "industry_jargon": "The tribe's shorthand.",
    "industry_acronyms": "Acronyms as credibility signals.",
    "technical_terms": "Speak their language.",
    "synonyms": "Other names for the same pain.",
    "customer_phrases": "Capture voice-of-customer — real quotes.",
    "desired_features": "Unmet demand — what users crave.",
    "missing_capabilities": "White space in the market.",
    "biggest_frustrations": "Emotional heat — why now.",
    "wish_statements": "Verbatim user desire.",
    "related_languages": "Technical context.",
    "related_frameworks": "Builder ecosystem.",
    "related_databases": "Data layer of the problem.",
    "cloud_providers": "Infra context.",
    "protocols": "How systems talk.",
    "standards": "What enterprise needs.",
    "regulations": "Market guardrails.",
    "compliance_requirements": "Deal-breakers for buyers.",
    "industry_standards": "Table stakes.",
    "file_formats": "Practical workflow detail.",
    "business_processes": "Where this sits in the org.",
    "solution": "The reveal — their product.",
    "how_it_solves": "Demo moment in words.",
    "why_choose_it": "Differentiation beat.",
    "founder_fit": "Founder story — why them.",
    "industry_experience": "Domain credibility.",
    "founder_skills": "Unfair advantages.",
    "why_switch": "Switching trigger.",
    "monetization": "Business model beat.",
    "paying_customers": "Economic buyer.",
    "why_pay": "Value justification.",
    "first_version": "Roadmap wedge.",
    "required_resources": "Ask — what do you need.",
    "biggest_risk": "Honest closing beat.",
}

CATEGORY_PITCH_HOOKS: dict[str, str] = {
    "problem": "Stay with the pain — make the audience feel it.",
    "customer": "Bring the customer to life — who are we rooting for?",
    "current_workflow": "The messy 'before' — set up the hero.",
    "ecosystem": "Landscape beat — who else is in the picture?",
    "industry_language": "How insiders talk — authenticity matters.",
    "customer_vocabulary": "Voice of customer — real words, not marketing speak.",
    "feature_requests": "Unmet demand — what's broken in the market?",
    "related_technologies": "Technical credibility — how it's built.",
    "market_context": "Rules and realities of the market.",
}

MIN_QUESTIONS = 15
MAX_QUESTIONS = 25

# Gap-fill (Q16–25) only targets these if still empty after core beats
CRITICAL_GAP_FIELDS: list[str] = [
    "company_name",
    "startup_idea",
    "core_problem",
    "target_customer",
    "customer_phrases",
    "competitors",
    "solution",
]

# Each beat = one pitch question targeting multiple fields. 15 core beats;
# optional gap-fill beats after core (up to MAX_QUESTIONS total).
PITCH_BEATS: list[dict[str, Any]] = [
    {
        "id": "intro",
        "fields": ["company_name", "startup_idea", "inspiration"],
        "description": "Opening — name, one-line idea, and what pulled them in.",
        "fallback": "What's your startup called, what does it do in one line, and why did you start it?",
        "pitch_hook": "Open the pitch — intro and origin in one breath.",
    },
    {
        "id": "problem",
        "fields": [
            "core_problem", "problem_when", "problem_frequency",
            "problem_pain_level", "unsolved_consequences",
        ],
        "description": "The pain — what it is, when it hits, how often, severity, stakes.",
        "fallback": "What's the core problem, when does it happen, how often, how painful is it (1–10), and what happens if it's not fixed?",
        "pitch_hook": "Make the pain visceral — frequency, severity, and stakes.",
    },
    {
        "id": "customer_who",
        "fields": ["target_customer", "customer_job_titles", "customer_technical_expertise"],
        "description": "Who feels this — the person, their role, how technical they are.",
        "fallback": "Who is your main user, what's their job, and how technical are they?",
        "pitch_hook": "Paint the buyer — a specific person, not a segment slide.",
    },
    {
        "id": "customer_where",
        "fields": ["customer_company_size", "customer_industry", "customer_sub_industry"],
        "description": "Where they live — company size, industry, niche wedge.",
        "fallback": "What size company are they at, and what industry or niche are you focused on?",
        "pitch_hook": "Anchor the beachhead market.",
    },
    {
        "id": "workflow",
        "fields": [
            "current_workflow", "manual_steps", "bottlenecks", "time_spent", "workarounds",
        ],
        "description": "Life before your product — process, pain points, time wasted, hacks.",
        "fallback": "How do people handle this today — what steps are manual, where does it break, how much time does it take, and what workarounds exist?",
        "pitch_hook": "The messy 'before' picture — set up the hero.",
    },
    {
        "id": "competition",
        "fields": ["competitors", "alternatives", "software_used", "why_switch"],
        "description": "Landscape — competitors, non-software alternatives, incumbents, switching story.",
        "fallback": "Who are your competitors, what do people use instead today, and why would they switch to you?",
        "pitch_hook": "Competitive landscape and the switching trigger.",
    },
    {
        "id": "ecosystem",
        "fields": ["apis_used", "integrations", "frameworks_used", "platforms_used"],
        "description": "Technical ecosystem — APIs, integrations, frameworks, platforms in the workflow.",
        "fallback": "What APIs, integrations, frameworks, and platforms are involved in this workflow?",
        "pitch_hook": "Meet users where they already build and buy.",
    },
    {
        "id": "customer_voice",
        "fields": [
            "customer_phrases", "biggest_frustrations", "wish_statements",
            "desired_features", "missing_capabilities",
        ],
        "description": "Voice of customer — real quotes, frustrations, wishes, unmet needs.",
        "fallback": "What do users actually say about this problem — common phrases, frustrations, wishes, and features they want?",
        "pitch_hook": "Voice of customer — real words, not marketing speak.",
    },
    {
        "id": "industry_language",
        "fields": [
            "industry_keywords", "industry_jargon", "industry_acronyms",
            "technical_terms", "synonyms",
        ],
        "description": "How insiders talk — keywords, jargon, acronyms, technical terms, synonyms.",
        "fallback": "What words, jargon, acronyms, and other names do people use for this problem?",
        "pitch_hook": "The tribe's language — authenticity and search signal.",
    },
    {
        "id": "tech_stack",
        "fields": [
            "related_languages", "related_frameworks", "related_databases",
            "cloud_providers", "protocols", "standards",
        ],
        "description": "Builder context — languages, frameworks, databases, cloud, protocols, standards.",
        "fallback": "What languages, frameworks, databases, cloud providers, and protocols are used in this space?",
        "pitch_hook": "Technical credibility — how it's built under the hood.",
    },
    {
        "id": "market_context",
        "fields": [
            "regulations", "compliance_requirements", "industry_standards",
            "file_formats", "business_processes",
        ],
        "description": "Market rules — regulations, compliance, standards, file formats, business processes.",
        "fallback": "What regulations and compliance rules apply, and what file formats or business processes are involved?",
        "pitch_hook": "Market realities and deal-breakers.",
    },
    {
        "id": "solution",
        "fields": ["solution", "how_it_solves", "why_choose_it"],
        "description": "The product — what it is, the magic moment, why pick you.",
        "fallback": "What are you building, how does it solve the problem, and why would someone choose it?",
        "pitch_hook": "The reveal — hero product and differentiation.",
    },
    {
        "id": "founder",
        "fields": ["founder_fit", "industry_experience", "founder_skills"],
        "description": "Founder story — why you, domain history, unfair advantages.",
        "fallback": "Why are you the right team to build this, and what's your background in this area?",
        "pitch_hook": "Founder-market fit story.",
    },
    {
        "id": "business",
        "fields": ["monetization", "paying_customers", "why_pay"],
        "description": "Business model — how you make money, who pays, why it's worth budget.",
        "fallback": "How do you make money, who pays, and why would they pay for this?",
        "pitch_hook": "Business model beat.",
    },
    {
        "id": "execution",
        "fields": ["first_version", "required_resources", "biggest_risk"],
        "description": "Roadmap — first wedge, what you need, biggest worry.",
        "fallback": "What's your first version, what do you need to build it, and what's the biggest risk?",
        "pitch_hook": "Close with the wedge, needs, and honest risk.",
    },
]

BEAT_BY_ID: dict[str, dict[str, Any]] = {b["id"]: b for b in PITCH_BEATS}
CORE_BEAT_IDS: list[str] = [b["id"] for b in PITCH_BEATS]

for field, desc in PITCH_DESCRIPTIONS.items():
    FIELD_DESCRIPTIONS[field] = desc
for field, question in PITCH_FALLBACKS.items():
    FALLBACK_QUESTIONS[field] = question

RESEARCH_CATEGORIES = [
    "problem",
    "customer",
    "current_workflow",
    "ecosystem",
    "industry_language",
    "customer_vocabulary",
    "feature_requests",
    "related_technologies",
    "market_context",
]

CATEGORY_MINIMUMS: dict[str, dict[str, Any]] = {}
for cat in RESEARCH_CATEGORIES:
    cat_fields = [f for f, c in FIELD_CATEGORIES.items() if c == cat]
    required_in_cat = [f for f in cat_fields if FIELD_TIERS[f] == "required"]
    CATEGORY_MINIMUMS[cat] = {
        "required": min(3, len(required_in_cat)),
        "fields": required_in_cat,
    }

SEARCH_SEED_MINIMUMS: dict[str, int] = {
    "keywords": 3,
    "pain_points": 2,
    "customer_segments": 1,
    "competitors": 1,
    "technologies": 2,
}

# Platform -> fields that enable search on that platform
PLATFORM_FIELDS: dict[str, list[str]] = {p: [] for p in SEARCH_PLATFORMS}
for field, platforms in FIELD_SEARCH_PLATFORMS.items():
    for p in platforms:
        PLATFORM_FIELDS[p].append(field)

# Platform -> search seed buckets that enable search
PLATFORM_SEED_BUCKETS: dict[str, list[str]] = {
    "reddit": ["keywords", "pain_points", "customer_segments"],
    "hackernews": ["keywords", "pain_points", "technologies"],
    "github": ["technologies", "frameworks", "software", "integrations"],
    "product_hunt": ["companies", "products", "competitors"],
    "google_trends": ["keywords", "industries", "customer_segments"],
}


def _field_is_filled(profile: StartupProfile, field: str) -> bool:
    value = getattr(profile, field, None)
    return value not in (None, "", [], {})


def _category_filled_count(profile: StartupProfile, category: str) -> int:
    fields = CATEGORY_MINIMUMS[category]["fields"]
    return sum(1 for f in fields if _field_is_filled(profile, f))


def category_minimum_met(profile: StartupProfile, category: str) -> bool:
    minimum = CATEGORY_MINIMUMS[category]["required"]
    return _category_filled_count(profile, category) >= minimum


def all_category_minimums_met(profile: StartupProfile) -> bool:
    return all(category_minimum_met(profile, cat) for cat in RESEARCH_CATEGORIES)


def search_seed_minimums_met(seeds: SearchSeeds) -> bool:
    for bucket, minimum in SEARCH_SEED_MINIMUMS.items():
        items = getattr(seeds, bucket, [])
        if len(items) < minimum:
            return False
    return True


def _platform_field_score(profile: StartupProfile, platform: str, missing_fields: list[str]) -> float:
    """0.0 = worst (nothing filled), 1.0 = all enabling fields filled."""
    fields = PLATFORM_FIELDS.get(platform, [])
    if not fields:
        return 1.0
    filled = sum(1 for f in fields if _field_is_filled(profile, f))
    return filled / len(fields)


def _platform_seed_score(seeds: SearchSeeds, platform: str) -> float:
    """0.0 = seed buckets empty, 1.0 = all seed minimums for platform met."""
    buckets = PLATFORM_SEED_BUCKETS.get(platform, [])
    if not buckets:
        return 1.0
    met = 0
    for bucket in buckets:
        minimum = SEARCH_SEED_MINIMUMS.get(bucket, 1)
        items = getattr(seeds, bucket, [])
        if len(items) >= minimum:
            met += 1
    return met / len(buckets)


def platform_readiness_score(
    profile: StartupProfile,
    seeds: SearchSeeds,
    platform: str,
    missing_fields: list[str],
) -> float:
    field_score = _platform_field_score(profile, platform, missing_fields)
    seed_score = _platform_seed_score(seeds, platform)
    return (field_score + seed_score) / 2


def get_platform_readiness_report(
    profile: StartupProfile,
    seeds: SearchSeeds,
    missing_fields: list[str],
) -> dict[str, float]:
    return {
        p: platform_readiness_score(profile, seeds, p, missing_fields)
        for p in SEARCH_PLATFORMS
    }


def find_next_missing_field(missing_fields: list[str]) -> str | None:
    """Return the next field to ask about, honoring REQUIRED_FIELDS order."""
    for field in REQUIRED_FIELDS:
        if field in missing_fields:
            return field
    return None


def find_next_priority_field(
    missing_fields: list[str],
    profile: StartupProfile,
    seeds: SearchSeeds,
) -> tuple[str | None, str]:
    """
    Pick the next field using gap-driven platform readiness.
    Returns (field_name, pitch_hook) for question phrasing — hooks are
    founder-facing conversation cues, never internal research jargon.
    """
    if not missing_fields:
        return None, ""

    field: str | None = None

    if not all_category_minimums_met(profile):
        platform_scores = {
            p: platform_readiness_score(profile, seeds, p, missing_fields)
            for p in SEARCH_PLATFORMS
        }
        worst_platform = min(platform_scores, key=platform_scores.get)

        candidates = [
            f for f in missing_fields
            if FIELD_TIERS.get(f) == "required"
            and worst_platform in FIELD_SEARCH_PLATFORMS.get(f, [])
        ]
        if candidates:
            candidates.sort(key=lambda f: FIELD_ORDER[f])
            field = candidates[0]
        else:
            cat_scores = {
                cat: _category_filled_count(profile, cat) / max(len(CATEGORY_MINIMUMS[cat]["fields"]), 1)
                for cat in RESEARCH_CATEGORIES
            }
            worst_cat = min(cat_scores, key=cat_scores.get)
            cat_candidates = [
                f for f in missing_fields
                if FIELD_CATEGORIES.get(f) == worst_cat and FIELD_TIERS.get(f) == "required"
            ]
            if cat_candidates:
                cat_candidates.sort(key=lambda f: FIELD_ORDER[f])
                field = cat_candidates[0]
    else:
        field = find_next_missing_field(missing_fields)

    if field is None:
        return None, ""

    category = FIELD_CATEGORIES.get(field)
    hook = FIELD_PITCH_HOOKS.get(field) or (
        CATEGORY_PITCH_HOOKS.get(category, "") if category else "Keep the pitch flowing naturally."
    )
    return field, hook


def get_beat(beat_id: str | None) -> dict[str, Any] | None:
    if not beat_id:
        return None
    if beat_id.startswith("gap:"):
        field = beat_id[4:]
        return {
            "id": beat_id,
            "fields": [field],
            "description": FIELD_DESCRIPTIONS.get(field, field),
            "fallback": PITCH_FALLBACKS.get(field, FALLBACK_QUESTIONS.get(field, "")),
            "pitch_hook": FIELD_PITCH_HOOKS.get(field, "Fill a quick gap in the story."),
        }
    return BEAT_BY_ID.get(beat_id)


def find_next_beat(
    beats_asked: list[str],
    questions_asked: int,
    missing_fields: list[str],
    profile: StartupProfile,
    seeds: SearchSeeds,
) -> tuple[str | None, str, list[str]]:
    """
    Pick the next pitch beat (or gap-fill field). Returns (beat_id, pitch_hook, target_fields).
    Core beats: 15 fixed questions. Optional gap-fill up to MAX_QUESTIONS.
    """
    if questions_asked >= MAX_QUESTIONS:
        return None, "", []

    for beat in PITCH_BEATS:
        if beat["id"] not in beats_asked:
            return beat["id"], beat["pitch_hook"], beat["fields"]

    # Core beats done — optional targeted gap-fill (still within budget)
    if questions_asked < MAX_QUESTIONS and missing_fields:
        for field in CRITICAL_GAP_FIELDS:
            if field in missing_fields:
                hook = FIELD_PITCH_HOOKS.get(field, "Quick follow-up on something important.")
                return f"gap:{field}", hook, [field]
        field, hook = find_next_priority_field(missing_fields, profile, seeds)
        if field:
            return f"gap:{field}", hook, [field]

    return None, "", []


def core_beats_complete(beats_asked: list[str]) -> bool:
    return all(bid in beats_asked for bid in CORE_BEAT_IDS)

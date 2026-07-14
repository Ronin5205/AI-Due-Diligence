# Startup Pitch Interviewer

A state-driven pitch engine, not a chatbot. **LangGraph owns the flow,
Pydantic owns the data, Gemini phrases the conversation.**

Founders experience a **pitch practice session** — warm, curious, story-driven.
Behind the scenes, the same conversation fills structured market-research data
for Reddit, Hacker News, GitHub, Product Hunt, and Google Trends.

## Architecture

```
startup_interview/
├── main.py                    # CLI loop — drives one graph.invoke() per user turn
├── models/
│   ├── schema.py               # StartupProfile, SearchSeeds, Intent (single source of truth)
│   └── state.py                # InterviewState (TypedDict) — what flows through the graph
├── llm/
│   └── gemini_client.py        # The ONLY file that talks to Gemini. 5 jobs:
│                                #   classify_intent / extract_information /
│                                #   extract_search_entities / generate_question /
│                                #   generate_summary
├── graph/
│   ├── question_bank.py        # Sections, tiers, platform readiness, priority selector
│   ├── validators.py           # Tier-aware missing fields, seed merge, completion rules
│   ├── nodes.py                # One function per graph node
│   ├── builder.py              # StateGraph wiring — ALL routing logic lives here
│   └── persistence.py          # JSON-file session save/load (with legacy field migration)
└── sessions/                   # Saved session state (gitignore this in real use)
```

### Why this split matters

The LLM is never asked "what should happen next?" — only "what is this
message?", "what facts are in it?", "what search entities can we extract?",
and "how do I ask the next pitch question naturally?" Every decision about
**which topic to explore next**, **whether the pitch is complete**, and
**whether a message is off-topic** is plain Python in `graph/`.

### Research-driven question selection

Instead of a fixed linear questionnaire, the backend continuously evaluates
whether enough signal has been captured for downstream search — but the
founder only hears natural pitch follow-ups, never internal research jargon.

## Data collected

### 10 research categories

1. **Problem** — core problem, when, frequency, pain level (1–10), consequences
2. **Customer** — target segment, job titles, company size, industry, expertise
3. **Current Workflow** — how solved today, manual steps, bottlenecks, time, workarounds
4. **Existing Ecosystem** — competitors, alternatives, software, APIs, integrations
5. **Industry Language** — keywords, jargon, acronyms, technical terms, synonyms
6. **Customer Vocabulary** — exact phrases users search or say (highest search value)
7. **Feature Requests** — desired features, missing capabilities, frustrations, "I wish..."
8. **Related Technologies** — languages, frameworks, databases, cloud, protocols
9. **Market Context** — regulations, compliance, standards, file formats, processes
10. **Search Seeds** — auto-extracted entity lists for recursive search generation

### Due-diligence sections (retained)

- Solution Design, Founder Fit, Business Model, Execution Plan

### Pitch beat flow (15–25 questions)

The interview runs **15 core compound questions** — each one invites a rich answer
that fills multiple profile fields at once. If critical fields are still empty after
the core beats, up to **10 gap-fill follow-ups** run (hard cap **25 questions**).

| Beat | Topics covered in one question |
|------|--------------------------------|
| 1 intro | name, idea, inspiration |
| 2 problem | core pain, timing, frequency, severity, stakes |
| 3–4 customer | persona, role, industry, segment |
| 5 workflow | status quo, bottlenecks, workarounds |
| 6–11 market | competition, ecosystem, voice of customer, language, tech, regulations |
| 12–15 close | solution, founder, business model, execution |

Multi-field extraction runs on every answer — the LLM pulls all stated or implied
facts, not just the primary beat field.

## Graph flow

```
START
  → intent_classification (LLM: classify only)
  → route by intent:
      greeting          → greeting_handler          → END
      end_interview     → end_interview              → END
      off_topic         → off_topic_handler          → END   (re-asks current_question)
      clarification_req → clarification_handler      → END   (LLM explains + restates)
      refusal           → refusal_handler → question_selector ┐
      answer/partial    → information_extraction               │
                            → validation (merge + seeds + contradictions)
                            → question_selector (gap-driven) ────┘
                            → completion_checker (tiered readiness)
                                → route by completed:
                                     True  → verification_summary → END
                                     False → question_generator   → END
```

Each `graph.invoke()` call handles exactly one user turn and returns a
partial `InterviewState` update, which `main.py` merges and persists.

## Setup

```bash
py -m pip install -r requirements.txt
cp .env.example .env   # from repo root; then edit .env with your real key
```

Environment files live at the **repository root** (`AI_Due_Diligence/.env`), not inside
`startup_interview/`. `main.py` loads them automatically when you run the CLI.

On Windows, use the **`py` launcher** — plain `python` may resolve to MSYS Python
without the project packages installed.

## Run

```bash
cd startup_interview
py main.py                 # starts a new session with a random id
py main.py my-session-123  # resumes (or starts) a specific session
```

On completion, the CLI prints:

1. Full profile JSON
2. **Search Seeds** block (ready for a downstream research engine)
3. Platform readiness report

Session state is persisted to `sessions/<session_id>.json` after every
turn, so you can kill the process and resume later with the same id.

## Extending

- **Add a field**: add it to `StartupProfile` in `models/schema.py`, add
  it to `EXTRACTABLE_FIELDS`, then add it to a section in
  `graph/question_bank.py` with `tier` and `search_platforms` metadata.
- **Adjust completion thresholds**: edit `CATEGORY_MINIMUMS` and
  `SEARCH_SEED_MINIMUMS` in `question_bank.py`.
- **Add a new intent branch** (e.g. "correction"): add the enum value
  to `Intent`, teach `_INTENT_SYSTEM` about it, add a handler node in
  `graph/nodes.py`, and wire it into `_route_after_intent` in
  `graph/builder.py`.
- **Swap persistence for a database**: `graph/persistence.py` is the
  only file that touches storage.
- **Swap the LLM provider**: `llm/gemini_client.py` is the only file
  that imports the Gemini SDK. Keep the five public function signatures.

## Search Seeds output contract

After the interview, `startup.search_seeds` contains:

```json
{
  "companies": [],
  "products": [],
  "technologies": [],
  "frameworks": [],
  "industries": [],
  "job_titles": [],
  "software": [],
  "workflows": [],
  "keywords": [],
  "pain_points": [],
  "feature_requests": [],
  "customer_segments": [],
  "integrations": [],
  "competitors": []
}
```

These are populated automatically from user answers via `extract_search_entities()`
and merged with case-insensitive deduplication after each turn.

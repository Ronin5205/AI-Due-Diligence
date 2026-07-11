# Startup Due Diligence Interviewer

A state-driven interview engine, not a chatbot. **LangGraph owns the flow,
Pydantic owns the data, Gemini only understands and phrases language.**

## Architecture

```
startup_interview/
├── main.py                    # CLI loop — drives one graph.invoke() per user turn
├── models/
│   ├── schema.py               # StartupProfile, Founder, Intent (single source of truth)
│   └── state.py                # InterviewState (TypedDict) — what flows through the graph
├── llm/
│   └── gemini_client.py        # The ONLY file that talks to Gemini. 4 jobs only:
│                                #   classify_intent / extract_information /
│                                #   generate_question / generate_summary
├── graph/
│   ├── question_bank.py        # Required fields, order, descriptions, fallback questions
│   ├── validators.py           # Sanity checks + contradiction detection (pure rules)
│   ├── nodes.py                # One function per graph node
│   ├── builder.py              # StateGraph wiring — ALL routing logic lives here
│   └── persistence.py          # JSON-file session save/load
└── sessions/                   # Saved session state (gitignore this in real use)
```

### Why this split matters

The LLM is never asked "what should happen next?" — only "what is this
message?", "what facts are in it?", "how do I phrase this field as a
question?", and "summarize this JSON." Every decision about **which
field to ask next**, **whether the interview is done**, **whether a
message is off-topic enough to redirect**, and **whether two answers
contradict each other** is plain Python in `graph/`. That's what makes
this an interview *engine* instead of a chatbot improvising its way
through a form.

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
                            → validation (merge + contradictions)
                            → question_selector ─────────────────┘
                            → completion_checker
                                → route by completed:
                                     True  → verification_summary → END
                                     False → question_generator   → END
```

Each `graph.invoke()` call handles exactly one user turn and returns a
partial `InterviewState` update, which `main.py` merges and persists.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then edit .env with your real key
export GEMINI_API_KEY=your_key_here
export GEMINI_MODEL=gemini-2.0-flash   # optional, this is the default
```

## Run

```bash
python main.py                 # starts a new session with a random id
python main.py my-session-123  # resumes (or starts) a specific session
```

Session state is persisted to `sessions/<session_id>.json` after every
turn, so you can kill the process and resume later with the same id.

## Extending

- **Add a required field**: add it to `StartupProfile` in
  `models/schema.py`, add it to `EXTRACTABLE_FIELDS`, then add it to
  `REQUIRED_FIELDS` + `FIELD_DESCRIPTIONS` + `FALLBACK_QUESTIONS` in
  `graph/question_bank.py`. Nothing in `llm/` or `graph/nodes.py`
  needs to change.
- **Add a new intent branch** (e.g. "correction"): add the enum value
  to `Intent`, teach `_INTENT_SYSTEM` about it, add a handler node in
  `graph/nodes.py`, and wire it into `_route_after_intent` in
  `graph/builder.py`.
- **Swap persistence for a database**: `graph/persistence.py` is the
  only file that touches storage — replace `save_session`/`load_session`
  with DB calls and nothing else changes.
- **Swap the LLM provider**: `llm/gemini_client.py` is the only file
  that imports the Gemini SDK. As long as the four public functions
  keep their signatures, nodes.py never needs to know.

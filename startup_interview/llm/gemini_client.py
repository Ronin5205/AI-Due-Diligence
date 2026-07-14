"""
Thin wrapper around the Gemini API.

This module is intentionally "dumb" — it has zero knowledge of
interview flow, required fields, or completion logic. It performs
exactly five jobs:

    1. classify_intent()         -> Intent
    2. extract_information()       -> dict (validated against schema fields)
    3. extract_search_entities()   -> dict[str, list[str]] (SearchSeeds buckets)
    4. generate_question()       -> str  (natural-language phrasing)
    5. generate_summary()          -> str  (verification summary)

Every call asks Gemini for JSON (mime type application/json) where
structure matters, and plain text where only phrasing matters. All
JSON is parsed defensively — a malformed response never crashes the
graph, it just degrades to a safe default and lets the backend nodes
decide what to do next.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from google import genai
from google.genai import types as genai_types

from models.schema import EXTRACTABLE_FIELDS, SEARCH_SEED_BUCKETS, Intent

_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
_client = None
_warned_missing_key = False


def _get_client():
    global _client, _warned_missing_key
    if _client is not None:
        return _client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        if not _warned_missing_key:
            print(
                "[gemini_client] WARNING: GEMINI_API_KEY is not set. "
                "All LLM calls will fail and the interview will fall back "
                "to static defaults (repeated fallback questions, intent "
                "always 'unknown'). Set it in your shell or in a .env file.",
                file=sys.stderr,
            )
            _warned_missing_key = True
        raise RuntimeError("GEMINI_API_KEY is not set.")
    _client = genai.Client(api_key=api_key)
    return _client


def _call_gemini_json(prompt: str, system_instruction: str, max_output_tokens: int):
    client = _get_client()
    return client.models.generate_content(
        model=_MODEL_NAME,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=max_output_tokens,
        ),
    )


def _safe_json_call(prompt: str, system_instruction: str, max_tokens: int = 512) -> dict[str, Any]:
    """Call Gemini in JSON mode and defensively parse the result."""
    text = ""
    try:
        response = _call_gemini_json(prompt, system_instruction, max_output_tokens=max_tokens)
        text = (response.text or "").strip()
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(
            f"[gemini_client] WARNING: JSON response looked truncated/malformed "
            f"({e}). Raw text: {text!r}. Retrying with more tokens...",
            file=sys.stderr,
        )
        try:
            retry_prompt = prompt + "\n\nReturn ONLY compact, complete, valid JSON. Do not truncate it."
            response = _call_gemini_json(retry_prompt, system_instruction, max_output_tokens=1024)
            text = (response.text or "").strip()
            return json.loads(text)
        except Exception as e2:
            print(f"[gemini_client] WARNING: retry also failed: {type(e2).__name__}: {e2}. Raw text: {text!r}", file=sys.stderr)
            return {}
    except Exception as e:
        print(f"[gemini_client] WARNING: Gemini call failed: {type(e).__name__}: {e}", file=sys.stderr)
        return {}


def _safe_text_call(prompt: str, system_instruction: str, temperature: float = 0.4) -> str:
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            ),
        )
        return (response.text or "").strip()
    except Exception as e:
        print(f"[gemini_client] WARNING: Gemini call failed: {type(e).__name__}: {e}", file=sys.stderr)
        return ""


_REACTION_PREFIXES = (
    "that sounds like",
    "that sounds",
    "interesting",
    "love that",
    "great ",
    "great,",
    "i see ",
    "i see that",
    "so you're",
    "so you are",
    "it seems like",
    "it sounds like",
    "thanks for sharing",
    "got it",
    "makes sense",
)


def _strip_question_reactions(text: str) -> str:
    """Remove common LLM reaction preambles from generated questions."""
    cleaned = text.strip().strip('"').strip("'")
    if not cleaned:
        return cleaned
    lower = cleaned.lower()
    for prefix in _REACTION_PREFIXES:
        if lower.startswith(prefix):
            # Drop everything through the first sentence break or em-dash
            for sep in (". ", " — ", " - ", "? ", "!\n"):
                idx = cleaned.find(sep)
                if idx != -1 and idx < 120:
                    cleaned = cleaned[idx + len(sep):].strip()
                    break
            else:
                # No separator — take after first comma if early
                comma = cleaned.find(", ")
                if comma != -1 and comma < 80:
                    cleaned = cleaned[comma + 2:].strip()
            break
    # Ensure ends with ?
    if cleaned and cleaned[-1] not in "?.":
        cleaned += "?"
    return cleaned[0].upper() + cleaned[1:] if cleaned else cleaned


# --------------------------------------------------------------------
# 1. Intent classification
# --------------------------------------------------------------------

_INTENT_SYSTEM = f"""You classify a single user message inside a founder pitch
conversation. The founder is telling their startup story; you only label the message.

Valid intents (return exactly one, lowercase, no other text):
{[i.value for i in Intent if i != Intent.UNKNOWN]}

Definitions:
- answer: directly and fully answers the current question
- partial_answer: answers the current question but is incomplete or vague
- clarification_request: user is asking what the question means or why it's asked
- off_topic: unrelated to the current question or the pitch
- refusal: user explicitly declines to answer
- greeting: small talk / hello with no substantive content
- end_interview: user wants to stop or end the session

Respond ONLY as JSON: {{"intent": "<one_of_the_above>"}}
"""


def classify_intent(user_message: str, current_field: str, current_question: str) -> Intent:
    prompt = (
        f"Current field being asked about: {current_field}\n"
        f"Current question shown to user: {current_question}\n"
        f"User message: {user_message}\n\n"
        "Classify this message."
    )
    result = _safe_json_call(prompt, _INTENT_SYSTEM)
    raw = str(result.get("intent", "")).strip().lower()
    try:
        return Intent(raw)
    except ValueError:
        return Intent.UNKNOWN


# --------------------------------------------------------------------
# 2. Structured extraction
# --------------------------------------------------------------------

_EXTRACTION_SYSTEM = f"""You extract structured startup facts from a founder's pitch answer.
One rich answer often covers MANY fields at once — extract every fact explicitly stated
or clearly implied. Be thorough; do not leave extractable facts on the table.

Allowed output fields:
{EXTRACTABLE_FIELDS}

Rules:
- Include every field the message states or clearly implies — aim for multiple fields per answer.
- Every value is a string. Combine list-like content into one string (comma-separated is fine).
- For vocabulary/phrase fields, preserve the founder's exact wording.
- For problem_pain_level, extract as a string number 1-10 if stated or implied.
- Never invent values. Never include null/empty fields.

Respond ONLY as JSON, e.g.:
{{"company_name": "Acme", "startup_idea": "AI invoice automation", "core_problem": "manual reconciliation", "customer_phrases": "API drift, invoice hell"}}
"""


def extract_information(
    user_message: str,
    current_field: str,
    target_fields: list[str] | None = None,
    profile_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    targets = target_fields or ([current_field] if current_field else [])
    context_line = ""
    if profile_context:
        context_line = f"\nAlready known (do not repeat unless updated): {json.dumps(profile_context, default=str)}\n"
    prompt = (
        f"Primary beat fields to listen for: {targets}\n"
        f"Also extract ANY other allowed fields mentioned in the message.\n"
        f"{context_line}"
        f"User message: {user_message}\n\n"
        "Extract all facts present — be aggressive about multi-field extraction."
    )
    result = _safe_json_call(prompt, _EXTRACTION_SYSTEM, max_tokens=1024)
    return {k: v for k, v in result.items() if k in EXTRACTABLE_FIELDS and v not in (None, "", [])}


# --------------------------------------------------------------------
# 3. Search entity extraction
# --------------------------------------------------------------------

_ENTITY_SYSTEM = f"""You extract concrete search entities from a user's interview
answer. These entities will be used to recursively generate searches on Reddit,
Hacker News, GitHub, Product Hunt, and Google Trends.

Output buckets (each value is a list of strings; omit empty buckets):
{SEARCH_SEED_BUCKETS}

Rules:
- Extract ONLY concrete nouns, product names, company names, phrases, job titles,
  technologies, pain points, and feature requests explicitly mentioned or clearly
  implied by the user's message.
- Preserve exact phrasing for pain points, keywords, and feature requests.
- Do not invent entities. Do not duplicate the same item across buckets unless
  it genuinely belongs in both.
- Keep items short (1-6 words each).

Respond ONLY as JSON, e.g.:
{{"companies": ["Stripe"], "keywords": ["API drift"], "pain_points": ["manual invoice processing"]}}
"""


def extract_search_entities(
    user_message: str,
    profile_context: dict[str, Any],
) -> dict[str, list[str]]:
    prompt = (
        f"Known context so far: {json.dumps(profile_context, default=str)}\n"
        f"User message: {user_message}\n\n"
        "Extract search entities from this message."
    )
    result = _safe_json_call(prompt, _ENTITY_SYSTEM, max_tokens=768)
    cleaned: dict[str, list[str]] = {}
    for bucket in SEARCH_SEED_BUCKETS:
        items = result.get(bucket, [])
        if not isinstance(items, list):
            continue
        cleaned[bucket] = [str(i).strip() for i in items if i and str(i).strip()]
    return cleaned


# --------------------------------------------------------------------
# 4. Question phrasing
# --------------------------------------------------------------------

_QUESTION_SYSTEM = """Write ONE clear question in plain, everyday English.

FORBIDDEN — never do these:
- No reaction openers: "That sounds like", "Interesting", "Love that", "Great",
  "I see", "So you're", "It seems", or any opinion about their startup.
- No praise, evaluation, or VC/investor voice.
- No preamble or transition ("Let's talk about...", "Tell me more about...").
- No bullet lists or numbered sub-questions.

STYLE:
- One sentence preferred; two short sentences max.
- Simple words anyone can understand.
- Ask directly. Sound like a normal person curious about their project.
- If you need several details, weave them with "and" — keep it conversational, not a form.

Output ONLY the question. Nothing else.
"""


def generate_question(
    field: str,
    field_description: str,
    profile_context: dict[str, Any],
    search_gap_context: str = "",
    beat_fields: list[str] | None = None,
    beat_fallback: str = "",
) -> str:
    # Minimal context — full profile causes repetitive "That sounds like X" openers
    company = profile_context.get("company_name")
    context_line = f"Company name (don't comment on it, just avoid re-asking): {company}" if company else ""
    guide = beat_fallback or field_description
    prompt = (
        f"Topics: {beat_fields or [field]}\n"
        f"Question guide (stay close to this, keep it short):\n{guide}\n"
        f"{context_line}\n\n"
        "Write one clean question."
    )
    text = _safe_text_call(prompt, _QUESTION_SYSTEM, temperature=0.2)
    return _strip_question_reactions(text)


_CLARIFY_SYSTEM = """The user asked what a question means. In plain English:
one short sentence explaining what you're asking for, then restate the question simply.
No opinions, no praise, no investor tone. Under 30 words total if possible.
"""


def generate_clarification(field: str, field_description: str, current_question: str) -> str:
    prompt = (
        f"Field: {field}\n"
        f"Meaning: {field_description}\n"
        f"Original question: {current_question}\n\n"
        "Explain briefly what info is needed, then restate the question."
    )
    text = _safe_text_call(prompt, _CLARIFY_SYSTEM)
    return text or current_question


# --------------------------------------------------------------------
# 5. Verification summary
# --------------------------------------------------------------------

_SUMMARY_SYSTEM = """Summarize what the founder shared in 2-3 short paragraphs of plain English.
Cover the problem, who it's for, and what they're building. End by asking if you got it
right. No investor jargon, no evaluation, no bullet lists.
"""


def generate_summary(profile_json: dict[str, Any], readiness_report: str = "") -> str:
    # readiness_report is internal only — not shown to founder in the prompt
    prompt = (
        f"What the founder shared:\n{json.dumps(profile_json, default=str, indent=2)}\n\n"
        "Write the pitch recap."
    )
    text = _safe_text_call(prompt, _SUMMARY_SYSTEM)
    return text

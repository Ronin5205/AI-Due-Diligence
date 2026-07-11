"""
Thin wrapper around the Gemini API.

This module is intentionally "dumb" — it has zero knowledge of
interview flow, required fields, or completion logic. It performs
exactly four jobs, matching the spec:

    1. classify_intent()      -> Intent
    2. extract_information()  -> dict (validated against schema fields)
    3. generate_question()    -> str  (natural-language phrasing)
    4. generate_summary()     -> str  (verification summary)

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

from models.schema import EXTRACTABLE_FIELDS, Intent

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


def _safe_json_call(prompt: str, system_instruction: str) -> dict[str, Any]:
    """Call Gemini in JSON mode and defensively parse the result.

    Explicitly sets max_output_tokens (some SDK/model defaults are low
    enough to truncate mid-object for JSON-mode responses) and retries
    once with more room + a stricter instruction if parsing still fails.
    """
    text = ""
    try:
        response = _call_gemini_json(prompt, system_instruction, max_output_tokens=512)
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


def _safe_text_call(prompt: str, system_instruction: str) -> str:
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4,
            ),
        )
        return (response.text or "").strip()
    except Exception as e:
        print(f"[gemini_client] WARNING: Gemini call failed: {type(e).__name__}: {e}", file=sys.stderr)
        return ""


# --------------------------------------------------------------------
# 1. Intent classification
# --------------------------------------------------------------------

_INTENT_SYSTEM = f"""You classify a single user message inside a structured
startup due-diligence interview. You do NOT conduct the interview and you
do NOT decide what happens next — you only label the message.

Valid intents (return exactly one, lowercase, no other text):
{[i.value for i in Intent if i != Intent.UNKNOWN]}

Definitions:
- answer: directly and fully answers the current question
- partial_answer: answers the current question but is incomplete or vague
- clarification_request: user is asking what the question means or why it's asked
- off_topic: unrelated to the current question or the interview
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

_EXTRACTION_SYSTEM = f"""You extract structured startup facts from a user's
message in a due-diligence interview. You do not ask questions or make
judgments — you only pull out facts that are EXPLICITLY stated.

Allowed output fields (omit any field not mentioned in the message):
{EXTRACTABLE_FIELDS}

Rules:
- Only include a field if the user's message actually states it.
- Every field is extracted as a string representing the user's response.
- Never invent values. Never include null/empty fields.

Respond ONLY as JSON, e.g.:
{{"company_name": "Acme Corp", "startup_idea": "SaaS for cats"}}
"""


def extract_information(user_message: str, current_field: str) -> dict[str, Any]:
    prompt = (
        f"The interview is currently focused on: {current_field}\n"
        f"User message: {user_message}\n\n"
        "Extract any startup facts explicitly present in this message."
    )
    result = _safe_json_call(prompt, _EXTRACTION_SYSTEM)
    # Defensive: drop any keys the schema doesn't know about
    return {k: v for k, v in result.items() if k in EXTRACTABLE_FIELDS and v not in (None, "", [])}


# --------------------------------------------------------------------
# 3. Question phrasing
# --------------------------------------------------------------------

_QUESTION_SYSTEM = """You phrase ONE natural, conversational interview
question for a startup founder, based on a field name and short context.
Keep it to one or two sentences. Do not add preamble, numbering, or
explanations. Do not ask about anything other than the given field.
"""


def generate_question(field: str, field_description: str, profile_context: dict[str, Any]) -> str:
    prompt = (
        f"Field to ask about: {field}\n"
        f"What this field means: {field_description}\n"
        f"Known context so far (for tone/continuity only): {json.dumps(profile_context, default=str)}\n\n"
        "Write the question."
    )
    text = _safe_text_call(prompt, _QUESTION_SYSTEM)
    return text


_CLARIFY_SYSTEM = """You briefly clarify what an interview question is
asking for, then restate the question. Two to three sentences maximum.
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
# 4. Verification summary
# --------------------------------------------------------------------

_SUMMARY_SYSTEM = """You write a clean, human-readable verification
summary of collected startup due-diligence data, formatted as a short
list of "Label: value" lines, followed by a single line asking the user
to confirm or correct anything. Omit fields with no value. No extra
commentary.
"""


def generate_summary(profile_json: dict[str, Any]) -> str:
    prompt = f"Collected data:\n{json.dumps(profile_json, default=str, indent=2)}\n\nWrite the summary."
    text = _safe_text_call(prompt, _SUMMARY_SYSTEM)
    return text
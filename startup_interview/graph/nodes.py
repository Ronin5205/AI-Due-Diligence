"""
Node functions. Each node takes InterviewState and returns a partial
state update (LangGraph merges these). Nodes call into llm.gemini_client
ONLY for the four narrow jobs described in the spec — routing, ordering,
validation, and completion logic all live here in plain Python.
"""
from __future__ import annotations

from models.schema import Intent, StartupProfile
from models.state import InterviewState
from graph import question_bank as qb
from graph import validators
from llm import gemini_client as llm


# --------------------------------------------------------------------
# Node 1: Intent Classification
# --------------------------------------------------------------------
def node_intent_classification(state: InterviewState) -> dict:
    intent = llm.classify_intent(
        user_message=state["last_user_message"],
        current_field=state.get("current_field") or "",
        current_question=state.get("current_question") or "",
    )
    return {"intent": intent.value}


# --------------------------------------------------------------------
# Node 2: Information Extraction
# --------------------------------------------------------------------
def node_information_extraction(state: InterviewState) -> dict:
    intent = state["intent"]
    if intent not in (Intent.ANSWER.value, Intent.PARTIAL_ANSWER.value):
        # Nothing to extract for greeting/off_topic/clarification/refusal/end
        return {"last_extraction": {}}

    extracted = llm.extract_information(
        user_message=state["last_user_message"],
        current_field=state.get("current_field") or "",
    )
    return {"last_extraction": extracted}


# --------------------------------------------------------------------
# Node 3: Validation (sanity checks + contradiction detection + merge)
# --------------------------------------------------------------------
def node_validation(state: InterviewState) -> dict:
    extracted = state.get("last_extraction") or {}
    startup = state["startup"]

    if not extracted:
        return {"validation_errors": [], "contradictions": state.get("contradictions", [])}

    errors = validators.validate_extracted_values(extracted)
    new_contradictions = validators.detect_contradictions(startup, extracted)

    if errors:
        # Reject the whole extraction batch on validation failure; do not
        # mutate the profile with bad data.
        return {
            "validation_errors": errors,
            "contradictions": state.get("contradictions", []) + new_contradictions,
        }

    # Merge into the canonical profile
    data = startup.model_dump()
    for field, value in extracted.items():
        data[field] = value

    updated_startup = StartupProfile(**data)
    skipped = state.get("skipped_fields", [])
    missing = validators.compute_missing_fields(updated_startup, skipped)

    return {
        "startup": updated_startup,
        "validation_errors": [],
        "contradictions": state.get("contradictions", []) + new_contradictions,
        "missing_fields": missing,
    }


# --------------------------------------------------------------------
# Node 4: Off-Topic Handler
# --------------------------------------------------------------------
def node_off_topic_handler(state: InterviewState) -> dict:
    streak = state.get("off_topic_streak", 0) + 1
    question = state.get("current_question") or "Could you answer the current question?"
    response = f"Let's stay focused on the startup assessment.\n\n{question}"
    return {"response_to_user": response, "off_topic_streak": streak}


def node_clarification_handler(state: InterviewState) -> dict:
    field = state.get("current_field") or ""
    description = qb.FIELD_DESCRIPTIONS.get(field, "")
    question = state.get("current_question") or ""
    clarification = llm.generate_clarification(field, description, question)
    return {"response_to_user": clarification}


def node_refusal_handler(state: InterviewState) -> dict:
    field = state.get("current_field")
    skipped = state.get("skipped_fields", [])
    if field and field not in skipped:
        skipped = skipped + [field]
    missing = validators.compute_missing_fields(state["startup"], skipped)
    return {"skipped_fields": skipped, "missing_fields": missing}


def node_greeting_handler(state: InterviewState) -> dict:
    question = state.get("current_question") or ""
    response = f"Hi! I'm here to walk through a quick due-diligence interview about your startup.\n\n{question}"
    return {"response_to_user": response}


# --------------------------------------------------------------------
# Node 5: Question Selector (pure rule engine, no LLM)
# --------------------------------------------------------------------
def node_question_selector(state: InterviewState) -> dict:
    missing = state.get("missing_fields", [])
    next_field = qb.find_next_missing_field(missing)
    return {"current_field": next_field}


# --------------------------------------------------------------------
# Node 6: Question Generator (LLM phrasing only)
# --------------------------------------------------------------------
def node_question_generator(state: InterviewState) -> dict:
    field = state.get("current_field")
    if field is None:
        return {"current_question": ""}

    description = qb.FIELD_DESCRIPTIONS.get(field, "")
    context = state["startup"].model_dump(exclude_none=True)
    question = llm.generate_question(field, description, context)
    if not question:
        question = qb.FALLBACK_QUESTIONS.get(field, f"Can you tell me about {field}?")

    return {"current_question": question, "response_to_user": question}


# --------------------------------------------------------------------
# Node 7: Completion Checker
# --------------------------------------------------------------------
def node_completion_checker(state: InterviewState) -> dict:
    completed = len(state.get("missing_fields", [])) == 0
    return {"completed": completed}


# --------------------------------------------------------------------
# Node 8: Verification Summary (LLM phrasing only, backend gates timing)
# --------------------------------------------------------------------
def node_verification_summary(state: InterviewState) -> dict:
    profile_json = state["startup"].model_dump(exclude_none=True)
    summary = llm.generate_summary(profile_json)
    if not summary:
        lines = [f"{k}: {v}" for k, v in profile_json.items()]
        summary = "Please verify the information collected:\n\n" + "\n".join(lines) + "\n\nIs anything incorrect?"
    return {"response_to_user": summary}


def node_end_interview(state: InterviewState) -> dict:
    return {"response_to_user": "Ending the interview here. Thanks for your time!", "completed": True}

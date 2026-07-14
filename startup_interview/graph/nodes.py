"""
Node functions. Each node takes InterviewState and returns a partial
state update (LangGraph merges these). Nodes call into llm.gemini_client
ONLY for the narrow jobs described in the spec — routing, ordering,
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
        return {"last_extraction": {}}

    extracted = llm.extract_information(
        user_message=state["last_user_message"],
        current_field=state.get("current_field") or "",
        target_fields=state.get("beat_fields") or [],
        profile_context=state["startup"].model_dump(exclude_none=True),
    )
    return {"last_extraction": extracted}


# --------------------------------------------------------------------
# Node 3: Validation (sanity checks + contradiction detection + merge)
# --------------------------------------------------------------------
def node_validation(state: InterviewState) -> dict:
    extracted = state.get("last_extraction") or {}
    startup = state["startup"]
    user_message = state.get("last_user_message", "")
    intent = state.get("intent", "")

    should_extract_seeds = (
        user_message.strip()
        and intent in (Intent.ANSWER.value, Intent.PARTIAL_ANSWER.value)
    )

    if not extracted:
        update: dict = {"validation_errors": [], "contradictions": state.get("contradictions", [])}
        if should_extract_seeds:
            profile_context = startup.model_dump(exclude_none=True)
            entities = llm.extract_search_entities(user_message, profile_context)
            merged_seeds = validators.merge_search_seeds(startup.search_seeds, entities)
            if merged_seeds != startup.search_seeds:
                startup = startup.model_copy(update={"search_seeds": merged_seeds})
                skipped = state.get("skipped_fields", [])
                update["startup"] = startup
                update["missing_fields"] = validators.compute_missing_fields(startup, skipped)
        return update

    errors = validators.validate_extracted_values(extracted)
    merged_data, new_contradictions = validators.merge_extracted_fields(startup, extracted)

    if errors:
        return {
            "validation_errors": errors,
            "contradictions": state.get("contradictions", []) + new_contradictions,
        }

    updated_startup = StartupProfile(**merged_data)

    if should_extract_seeds:
        profile_context = updated_startup.model_dump(exclude_none=True)
        entities = llm.extract_search_entities(user_message, profile_context)
        merged_seeds = validators.merge_search_seeds(updated_startup.search_seeds, entities)
        updated_startup = updated_startup.model_copy(update={"search_seeds": merged_seeds})

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
    question = state.get("current_question") or "What were you saying about your project?"
    response = f"Back to your project — {question}"
    return {"response_to_user": response, "off_topic_streak": streak}


def node_clarification_handler(state: InterviewState) -> dict:
    field = state.get("current_field") or ""
    description = qb.FIELD_DESCRIPTIONS.get(field, "")
    question = state.get("current_question") or ""
    clarification = llm.generate_clarification(field, description, question)
    return {"response_to_user": clarification}


def node_refusal_handler(state: InterviewState) -> dict:
    beat = state.get("current_beat")
    beats_asked = list(state.get("beats_asked", []))
    if beat and beat not in beats_asked:
        beats_asked.append(beat)
    skipped = state.get("skipped_fields", [])
    if state.get("current_field") and state["current_field"] not in skipped:
        skipped = skipped + [state["current_field"]]
    missing = validators.compute_missing_fields(state["startup"], skipped)
    return {"beats_asked": beats_asked, "skipped_fields": skipped, "missing_fields": missing}


def node_greeting_handler(state: InterviewState) -> dict:
    question = state.get("current_question") or ""
    response = f"Hi — {question}" if question else "Hi — tell me about your startup."
    return {"response_to_user": response}


# --------------------------------------------------------------------
# Node 5: Question Selector (gap-driven priority, no LLM routing)
# --------------------------------------------------------------------
def node_question_selector(state: InterviewState) -> dict:
    beats_asked = list(state.get("beats_asked", []))
    current_beat = state.get("current_beat")
    if current_beat and current_beat not in beats_asked and state.get("last_user_message"):
        beats_asked.append(current_beat)

    missing = state.get("missing_fields", [])
    profile = state["startup"]
    seeds = profile.search_seeds
    questions_asked = state.get("questions_asked", 0)

    next_beat, hook, beat_fields = qb.find_next_beat(
        beats_asked, questions_asked, missing, profile, seeds
    )
    primary_field = beat_fields[0] if beat_fields else None
    return {
        "beats_asked": beats_asked,
        "current_beat": next_beat,
        "current_field": primary_field,
        "beat_fields": beat_fields,
        "search_gap_context": hook,
    }


# --------------------------------------------------------------------
# Node 6: Question Generator (LLM phrasing only)
# --------------------------------------------------------------------
def node_question_generator(state: InterviewState) -> dict:
    beat_id = state.get("current_beat")
    if beat_id is None:
        return {"current_question": ""}

    beat = qb.get_beat(beat_id)
    if not beat:
        return {"current_question": ""}

    field = state.get("current_field") or beat["fields"][0]
    fallback = beat.get("fallback") or qb.FALLBACK_QUESTIONS.get(field, "")

    # Pre-written fallbacks — direct, plain English, no LLM reaction fluff
    question = fallback or f"What can you tell me about {field}?"

    return {
        "current_question": question,
        "response_to_user": question,
        "questions_asked": state.get("questions_asked", 0) + 1,
    }


# --------------------------------------------------------------------
# Node 7: Completion Checker (tiered readiness)
# --------------------------------------------------------------------
def node_completion_checker(state: InterviewState) -> dict:
    skipped = state.get("skipped_fields", [])
    completed = validators.is_interview_complete(
        state["startup"],
        skipped,
        state.get("questions_asked", 0),
        state.get("beats_asked", []),
    )
    return {"completed": completed}


# --------------------------------------------------------------------
# Node 8: Verification Summary (LLM phrasing only, backend gates timing)
# --------------------------------------------------------------------
def node_verification_summary(state: InterviewState) -> dict:
    profile_json = state["startup"].model_dump(exclude_none=True)
    missing = state.get("missing_fields", [])
    readiness = validators.format_readiness_report(
        state["startup"], missing,
        questions_asked=state.get("questions_asked", 0),
        beats_asked=state.get("beats_asked", []),
    )
    summary = llm.generate_summary(profile_json, readiness)
    if not summary:
        company = state["startup"].company_name or "your startup"
        idea = state["startup"].startup_idea or ""
        problem = state["startup"].core_problem or ""
        summary = (
            f"Here's what I heard about {company}:\n\n"
            f"{idea}\n\n"
            f"You're going after: {problem}\n\n"
            "Did I capture your story right — anything you'd change or add?"
        )
    return {"response_to_user": summary}


def node_end_interview(state: InterviewState) -> dict:
    return {
        "response_to_user": "Great pitch — thanks for sharing. Best of luck building!",
        "completed": True,
    }

"""
LangGraph state container. This is what actually flows through the
graph on every turn. It wraps a StartupProfile plus all the bookkeeping
the backend needs to control the interview — none of which the LLM
ever touches directly.
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict

from models.schema import StartupProfile


class InterviewState(TypedDict, total=False):
    # Canonical data
    startup: StartupProfile

    # Turn bookkeeping
    session_id: str
    last_user_message: str
    conversation_history: list[dict[str, str]]

    # Flow control (backend-owned, LLM never sets these)
    current_field: Optional[str]
    current_question: str
    intent: str
    missing_fields: list[str]
    contradictions: list[str]
    validation_errors: list[str]
    off_topic_streak: int
    skipped_fields: list[str]

    # Output for this turn — what the CLI/UI should show the user
    response_to_user: str
    completed: bool

    # Raw extraction payload for the current turn, kept for debugging/audit
    last_extraction: dict[str, Any]


def new_state(session_id: str) -> InterviewState:
    return InterviewState(
        startup=StartupProfile(),
        session_id=session_id,
        last_user_message="",
        conversation_history=[],
        current_field=None,
        current_question="",
        intent="",
        missing_fields=[],
        contradictions=[],
        validation_errors=[],
        off_topic_streak=0,
        skipped_fields=[],
        response_to_user="",
        completed=False,
        last_extraction={},
    )

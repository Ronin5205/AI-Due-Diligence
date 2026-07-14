"""
Minimal session persistence. Swap this out for a database in production;
the interface (save_session / load_session) is what matters.
"""
from __future__ import annotations

import json
import os

from models.schema import LEGACY_FIELD_ALIASES, SearchSeeds, StartupProfile
from models.state import InterviewState, new_state

_SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sessions")


def _path(session_id: str) -> str:
    os.makedirs(_SESSIONS_DIR, exist_ok=True)
    return os.path.join(_SESSIONS_DIR, f"{session_id}.json")


def _migrate_startup_data(data: dict) -> dict:
    """Map legacy field names to current schema and ensure search_seeds exists."""
    migrated = dict(data)
    for old_name, new_name in LEGACY_FIELD_ALIASES.items():
        if old_name in migrated and new_name not in migrated:
            migrated[new_name] = migrated.pop(old_name)
        elif old_name in migrated:
            migrated.pop(old_name)

    if "search_seeds" not in migrated:
        migrated["search_seeds"] = SearchSeeds().model_dump()
    elif isinstance(migrated["search_seeds"], dict):
        migrated["search_seeds"] = SearchSeeds(**migrated["search_seeds"]).model_dump()

    return migrated


def save_session(state: InterviewState) -> None:
    serializable = dict(state)
    serializable["startup"] = state["startup"].model_dump()
    with open(_path(state["session_id"]), "w") as f:
        json.dump(serializable, f, indent=2, default=str)


def load_session(session_id: str) -> InterviewState:
    path = _path(session_id)
    if not os.path.exists(path):
        return new_state(session_id)
    with open(path) as f:
        data = json.load(f)
    startup_data = _migrate_startup_data(data.get("startup", {}))
    data["startup"] = StartupProfile(**startup_data)
    if "search_gap_context" not in data:
        data["search_gap_context"] = ""
    if "questions_asked" not in data:
        data["questions_asked"] = 0
    if "beats_asked" not in data:
        data["beats_asked"] = []
    if "current_beat" not in data:
        data["current_beat"] = None
    if "beat_fields" not in data:
        data["beat_fields"] = []
    return InterviewState(**data)


def session_exists(session_id: str) -> bool:
    return os.path.exists(_path(session_id))

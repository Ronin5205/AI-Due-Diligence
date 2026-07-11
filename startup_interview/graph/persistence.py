"""
Minimal session persistence. Swap this out for a database in production;
the interface (save_session / load_session) is what matters.
"""
from __future__ import annotations

import json
import os

from models.schema import StartupProfile
from models.state import InterviewState, new_state

_SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sessions")


def _path(session_id: str) -> str:
    os.makedirs(_SESSIONS_DIR, exist_ok=True)
    return os.path.join(_SESSIONS_DIR, f"{session_id}.json")


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
    data["startup"] = StartupProfile(**data["startup"])
    return InterviewState(**data)


def session_exists(session_id: str) -> bool:
    return os.path.exists(_path(session_id))

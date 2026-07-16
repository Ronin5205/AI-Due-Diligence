"""Load and validate interview session JSON files."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INTERVIEW_DIR = _PROJECT_ROOT / "startup_interview"
_SESSIONS_DIR = _INTERVIEW_DIR / "sessions"

# Import interview schema via normal package path (required for Pydantic model resolution).
if str(_INTERVIEW_DIR) not in sys.path:
    sys.path.insert(0, str(_INTERVIEW_DIR))

from models.schema import SearchSeeds, StartupProfile  # noqa: E402


def _migrate_startup_data(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    if "search_seeds" not in migrated:
        migrated["search_seeds"] = SearchSeeds().model_dump()
    elif isinstance(migrated["search_seeds"], dict):
        migrated["search_seeds"] = SearchSeeds(**migrated["search_seeds"]).model_dump()
    return migrated


def load_session(session_id: str) -> dict[str, Any]:
    path = _SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    startup_data = _migrate_startup_data(data.get("startup", {}))
    startup = StartupProfile(**startup_data)
    return {
        "session_id": data.get("session_id", session_id),
        "startup": startup,
        "completed": data.get("completed", False),
        "missing_fields": data.get("missing_fields", []),
        "raw": data,
    }


def list_sessions() -> list[str]:
    if not _SESSIONS_DIR.exists():
        return []
    return sorted(p.stem for p in _SESSIONS_DIR.glob("*.json"))

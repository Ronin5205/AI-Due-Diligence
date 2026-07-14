"""
CLI driver for the Startup Pitch Interviewer.

Usage:
    export GEMINI_API_KEY=your_key_here   # or set in repo-root .env
    py main.py [session_id]

Each user turn invokes the compiled LangGraph exactly once. The graph
returns a partial state update; we merge it, persist it, and print
`response_to_user`. The founder experiences a pitch conversation; the
backend still collects structured research data behind the scenes.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json
import uuid
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    print(
        "Missing dependencies.\n\n"
        "From the repo root, install them with:\n"
        "  py -m pip install -r requirements.txt\n\n"
        "Then run the CLI with:\n"
        "  py main.py\n\n"
        "On Windows, plain `python` may point at MSYS Python without these packages.",
        file=sys.stderr,
    )
    raise SystemExit(1)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

from graph.builder import build_graph
from graph.persistence import save_session, load_session
from graph import question_bank as qb
from graph import validators
from graph.nodes import node_question_generator


def bootstrap_state(session_id: str):
    state = load_session(session_id)
    if not state.get("current_question"):
        startup = state["startup"]
        state["missing_fields"] = validators.compute_missing_fields(
            startup, state.get("skipped_fields", [])
        )
        beat_id, hook, beat_fields = qb.find_next_beat(
            state.get("beats_asked", []),
            state.get("questions_asked", 0),
            state["missing_fields"],
            startup,
            startup.search_seeds,
        )
        state["current_beat"] = beat_id
        state["current_field"] = beat_fields[0] if beat_fields else None
        state["beat_fields"] = beat_fields
        state["search_gap_context"] = hook
        update = node_question_generator(state)
        state.update(update)
    return state


def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4())[:8]
    print(f"[session: {session_id}]")

    graph = build_graph()
    state = bootstrap_state(session_id)

    print(f"\nInterviewer: {state['current_question']}\n")

    while not state.get("completed"):
        try:
            user_message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession paused. Resume later with the same session id.")
            save_session(state)
            return

        if not user_message:
            continue

        state["last_user_message"] = user_message
        state["conversation_history"] = state.get("conversation_history", []) + [
            {"role": "user", "content": user_message}
        ]

        result = graph.invoke(state)
        state.update(result)

        reply = state.get("response_to_user", "")
        if reply:
            state["conversation_history"].append({"role": "assistant", "content": reply})
            print(f"\nInterviewer: {reply}\n")

        save_session(state)

        if state.get("completed"):
            break

    startup = state["startup"]
    missing = state.get("missing_fields", [])

    print("Interview complete.\n")
    print("=" * 60)
    print("FINAL PROFILE")
    print("=" * 60)
    print(startup.model_dump_json(indent=2, exclude={"search_seeds"}))

    print("\n" + "=" * 60)
    print("SEARCH SEEDS (for research engine handoff)")
    print("=" * 60)
    print(json.dumps(startup.search_seeds.model_dump(), indent=2))

    print("\n" + "=" * 60)
    print("READINESS REPORT")
    print("=" * 60)
    print(validators.format_readiness_report(
        startup, missing,
        questions_asked=state.get("questions_asked", 0),
        beats_asked=state.get("beats_asked", []),
    ))


if __name__ == "__main__":
    main()

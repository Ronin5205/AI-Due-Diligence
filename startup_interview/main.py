"""
CLI driver for the Startup Due Diligence Interviewer.

Usage:
    export GEMINI_API_KEY=your_key_here
    python main.py [session_id]

Each user turn invokes the compiled LangGraph exactly once. The graph
returns a partial state update; we merge it, persist it, and print
`response_to_user`. All flow decisions (what question comes next,
whether the interview is complete, whether to redirect off-topic
messages) are made by graph.builder / graph.nodes — never by the LLM.
"""
from __future__ import annotations

import sys
import uuid

from graph.builder import build_graph
from graph.persistence import save_session, load_session
from graph import question_bank as qb
from graph.nodes import node_question_generator


def bootstrap_state(session_id: str):
    state = load_session(session_id)
    if not state.get("current_question"):
        # First-ever turn: seed the first question directly (no user
        # message to classify yet).
        state["missing_fields"] = qb.REQUIRED_FIELDS.copy()
        state["current_field"] = qb.find_next_missing_field(state["missing_fields"])
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

    print("Interview complete. Final profile:")
    print(state["startup"].model_dump_json(indent=2))


if __name__ == "__main__":
    main()

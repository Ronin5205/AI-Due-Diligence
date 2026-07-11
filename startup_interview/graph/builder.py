"""
Graph wiring. This is the only place that decides "what happens next" —
every edge condition reads backend state (intent, missing_fields,
completed), never anything the LLM freely narrates.

Flow (matches the spec):

    START
      -> intent_classification
      -> route by intent:
           greeting         -> greeting_handler                -> END
           end_interview    -> end_interview                   -> END
           off_topic        -> off_topic_handler                -> END
           clarification    -> clarification_handler            -> END
           refusal          -> refusal_handler -> question_selector -> question_generator -> END
           answer/partial   -> information_extraction -> validation
                                 -> question_selector -> completion_checker
                                 -> route by completed:
                                      True  -> verification_summary -> END
                                      False -> question_generator   -> END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from models.schema import Intent
from models.state import InterviewState
from graph import nodes


def _route_after_intent(state: InterviewState) -> str:
    intent = state["intent"]
    mapping = {
        Intent.GREETING.value: "greeting_handler",
        Intent.END_INTERVIEW.value: "end_interview",
        Intent.OFF_TOPIC.value: "off_topic_handler",
        Intent.CLARIFICATION_REQUEST.value: "clarification_handler",
        Intent.REFUSAL.value: "refusal_handler",
        Intent.ANSWER.value: "information_extraction",
        Intent.PARTIAL_ANSWER.value: "information_extraction",
    }
    return mapping.get(intent, "information_extraction")  # UNKNOWN falls back to trying extraction


def _route_after_completion(state: InterviewState) -> str:
    return "verification_summary" if state.get("completed") else "question_generator"


def build_graph():
    graph = StateGraph(InterviewState)

    # Register nodes
    graph.add_node("intent_classification", nodes.node_intent_classification)
    graph.add_node("information_extraction", nodes.node_information_extraction)
    graph.add_node("validation", nodes.node_validation)
    graph.add_node("off_topic_handler", nodes.node_off_topic_handler)
    graph.add_node("clarification_handler", nodes.node_clarification_handler)
    graph.add_node("refusal_handler", nodes.node_refusal_handler)
    graph.add_node("greeting_handler", nodes.node_greeting_handler)
    graph.add_node("question_selector", nodes.node_question_selector)
    graph.add_node("question_generator", nodes.node_question_generator)
    graph.add_node("completion_checker", nodes.node_completion_checker)
    graph.add_node("verification_summary", nodes.node_verification_summary)
    graph.add_node("end_interview", nodes.node_end_interview)

    graph.set_entry_point("intent_classification")

    # Branch immediately on intent
    graph.add_conditional_edges(
        "intent_classification",
        _route_after_intent,
        {
            "greeting_handler": "greeting_handler",
            "end_interview": "end_interview",
            "off_topic_handler": "off_topic_handler",
            "clarification_handler": "clarification_handler",
            "refusal_handler": "refusal_handler",
            "information_extraction": "information_extraction",
        },
    )

    # Terminal, single-turn branches
    graph.add_edge("greeting_handler", END)
    graph.add_edge("end_interview", END)
    graph.add_edge("off_topic_handler", END)
    graph.add_edge("clarification_handler", END)

    # Refusal skips the field and moves on to the next question
    graph.add_edge("refusal_handler", "question_selector")

    # Main answer path
    graph.add_edge("information_extraction", "validation")
    graph.add_edge("validation", "question_selector")
    graph.add_edge("question_selector", "completion_checker")

    graph.add_conditional_edges(
        "completion_checker",
        _route_after_completion,
        {
            "verification_summary": "verification_summary",
            "question_generator": "question_generator",
        },
    )

    graph.add_edge("question_generator", END)
    graph.add_edge("verification_summary", END)

    return graph.compile()

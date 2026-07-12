"""LangGraph wiring:

planner -> retriever -> structured_query -> calculator -> reasoner -> verifier
               ^                                                        |
               +------------- low confidence (one retry) ---------------+
                                                                        v
                                                                      output
"""

import uuid
from functools import partial

from langgraph.graph import END, StateGraph

from app.agents.calculator import calculate
from app.agents.planner import plan
from app.agents.reasoner import reason
from app.agents.retriever import retrieve
from app.agents.state import AgentState, Services
from app.agents.structured_query import structured_query
from app.agents.verifier import should_retry, verify


def _output(state: AgentState, services: Services) -> AgentState:
    warnings = []
    if state.get("confidence", 0) < services.min_confidence:
        warnings.append(
            "Low confidence: the answer could not be fully verified against the documents. "
            "Consider rephrasing the question or uploading the relevant document."
        )
        warnings.extend(state.get("issues", []))
    return {
        "answer": state.get("draft", ""),
        "sources": state.get("draft_sources", []),
        "warnings": warnings,
    }


def build_graph(services: Services):
    graph = StateGraph(AgentState)
    graph.add_node("planner", partial(plan, services=services))
    graph.add_node("retriever", partial(retrieve, services=services))
    graph.add_node("structured_query", partial(structured_query, services=services))
    graph.add_node("calculator", partial(calculate, services=services))
    graph.add_node("reasoner", partial(reason, services=services))
    graph.add_node("verifier", partial(verify, services=services))
    graph.add_node("output", partial(_output, services=services))

    graph.set_entry_point("planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "structured_query")
    graph.add_edge("structured_query", "calculator")
    graph.add_edge("calculator", "reasoner")
    graph.add_edge("reasoner", "verifier")
    graph.add_conditional_edges(
        "verifier",
        lambda state: "retry" if should_retry(state, services) else "done",
        {"retry": "retriever", "done": "output"},
    )
    graph.add_edge("output", END)
    return graph.compile()


def run_query(
    services: Services,
    question: str,
    category: str | None = None,
    family_member: str | None = None,
) -> AgentState:
    app = build_graph(services)
    initial: AgentState = {
        "question": question,
        "category": category,
        "family_member": family_member,
        "query_id": uuid.uuid4().hex,
        "retry_count": 0,
    }
    return app.invoke(initial)

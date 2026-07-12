"""Planner: decomposes the user question into steps and search queries."""

from app.agents.state import AgentState, Services
from app.config import get_settings

SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {"type": "array", "items": {"type": "string"}},
        "search_queries": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["steps", "search_queries"],
    "additionalProperties": False,
}

SYSTEM = """You are the planning agent of a family-document assistant (loans, utilities,
medical, property; documents are often in Russian). Break the user's question into
concrete steps and produce 1-3 retrieval queries (in the question's language) that will
find the relevant document passages."""


def plan(state: AgentState, services: Services) -> AgentState:
    data = services.llm.complete_json(
        model=get_settings().planner_model,
        system=SYSTEM,
        prompt=f"Question: {state['question']}",
        schema=SCHEMA,
    )
    services.audit(state["query_id"], "planner", data)
    return {"plan": data["steps"], "search_queries": data["search_queries"] or [state["question"]]}

"""Structured Query: pulls exact figures (payments, dates, amounts) from Postgres.

Starter scope: fetches the payments/entities matching the metadata filters.
TODO: LLM -> parameterized SQL synthesis for arbitrary structured questions.
"""

from app.agents.state import AgentState, Services


def structured_query(state: AgentState, services: Services) -> AgentState:
    facts = services.fetch_structured(state.get("category"), state.get("family_member"))
    services.audit(state["query_id"], "structured_query", {"facts": len(facts)})
    return {"structured_facts": facts}

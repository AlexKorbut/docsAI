"""Retriever: runs hybrid search for each planned query and merges hits."""

from typing import Any

from app.agents.state import AgentState, Services


def retrieve(state: AgentState, services: Services) -> AgentState:
    queries = state.get("search_queries") or [state["question"]]
    merged: dict[int, dict[str, Any]] = {}
    for query in queries:
        for hit in services.retrieve(query, state.get("category"), state.get("family_member")):
            existing = merged.get(hit["chunk_id"])
            if existing is None or hit["score"] > existing["score"]:
                merged[hit["chunk_id"]] = hit
    hits = sorted(merged.values(), key=lambda h: h["score"], reverse=True)[:12]
    services.audit(
        state["query_id"], "retriever", {"queries": queries, "hits": [h["chunk_id"] for h in hits]}
    )
    return {"hits": hits}

"""Reasoner: synthesizes a draft answer strictly from retrieved evidence."""

import json

from app.agents.state import AgentState, Services
from app.config import get_settings

SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "cited_chunk_ids": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["answer", "cited_chunk_ids"],
    "additionalProperties": False,
}

SYSTEM = """You are the reasoning agent of a family-document assistant. Answer the
user's question in the question's language, using ONLY the provided evidence:
document passages, exact structured facts from the database, and pre-computed
calculations. Rules:
- Every factual claim must come from the evidence; never rely on outside knowledge.
- For amounts and dates, prefer the structured facts and calculations — they are
  exact database values.
- Reference documents by title and date in the answer.
- If the evidence is insufficient, say so explicitly instead of guessing.
List the ids of every passage you actually used in cited_chunk_ids."""


def reason(state: AgentState, services: Services) -> AgentState:
    evidence = {
        "passages": [
            {
                "chunk_id": h["chunk_id"],
                "document": h["document_title"],
                "section": h.get("section"),
                "text": h["text"],
            }
            for h in state.get("hits", [])
        ],
        "structured_facts": state.get("structured_facts", []),
        "calculations": state.get("calculations", []),
    }
    data = services.llm.complete_json(
        model=get_settings().reasoner_model,
        system=SYSTEM,
        prompt=(
            f"Question: {state['question']}\n\n"
            f"Evidence:\n{json.dumps(evidence, ensure_ascii=False, default=str)}"
        ),
        schema=SCHEMA,
    )
    cited = set(data["cited_chunk_ids"])
    sources = [
        {
            "document_id": h["document_id"],
            "document_title": h["document_title"],
            "page": h.get("page"),
            "section": h.get("section"),
            "snippet": h["text"][:300],
        }
        for h in state.get("hits", [])
        if h["chunk_id"] in cited
    ]
    services.audit(state["query_id"], "reasoner", {"answer": data["answer"], "cited": list(cited)})
    return {"draft": data["answer"], "draft_sources": sources}

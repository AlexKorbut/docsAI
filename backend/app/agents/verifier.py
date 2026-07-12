"""Verifier: the accuracy gate. Checks every claim in the draft against the evidence,
scores confidence 0-100, and can send the pipeline back to retrieval."""

import json

from app.agents.state import AgentState, Services
from app.config import get_settings

SCHEMA = {
    "type": "object",
    "properties": {
        "confidence": {"type": "integer"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "corrected_answer": {"type": ["string", "null"]},
    },
    "required": ["confidence", "issues", "corrected_answer"],
    "additionalProperties": False,
}

SYSTEM = """You are the verification agent — the last line of defense against errors
in a family-document assistant where mistakes about money, debts, and dates are costly.
Adversarially check the draft answer against the evidence:
- Verify every number, date, name, and document reference appears in the evidence.
- Check amounts against the exact structured facts, not the free-text passages.
- Look for contradictions between documents and for claims with no supporting source.
Return a confidence score 0-100 (100 = every claim verified against evidence),
a list of concrete issues found, and — if the issues are minor and fixable from the
evidence alone — a corrected answer. If evidence is missing, lower the confidence
instead of guessing."""


def verify(state: AgentState, services: Services) -> AgentState:
    evidence = {
        "passages": [
            {"chunk_id": h["chunk_id"], "document": h["document_title"], "text": h["text"]}
            for h in state.get("hits", [])
        ],
        "structured_facts": state.get("structured_facts", []),
        "calculations": state.get("calculations", []),
    }
    data = services.llm.complete_json(
        model=get_settings().verifier_model,
        system=SYSTEM,
        prompt=(
            f"Question: {state['question']}\n\n"
            f"Draft answer:\n{state.get('draft', '')}\n\n"
            f"Evidence:\n{json.dumps(evidence, ensure_ascii=False, default=str)}"
        ),
        schema=SCHEMA,
    )
    confidence = max(0, min(100, data["confidence"]))
    services.audit(
        state["query_id"], "verifier", {"confidence": confidence, "issues": data["issues"]}
    )
    result: AgentState = {
        "confidence": confidence,
        "issues": data["issues"],
        "retry_count": state.get("retry_count", 0) + 1,
    }
    if data.get("corrected_answer"):
        result["draft"] = data["corrected_answer"]
    return result


def should_retry(state: AgentState, services: Services) -> bool:
    return (
        state.get("confidence", 0) < services.min_confidence
        and state.get("retry_count", 0) <= services.max_retries
    )

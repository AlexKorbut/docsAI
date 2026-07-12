"""Builds the production `Services` container used by the agent graph."""

from dataclasses import asdict
from typing import Any

from sqlalchemy.orm import Session

from app.agents.state import Services
from app.config import get_settings
from app.llm.anthropic_client import get_llm
from app.llm.embeddings import get_embedder
from app.retrieval.hybrid import hybrid_search
from app.storage.models import AgentRun, Document, Payment


def build_services(db: Session) -> Services:
    embedder = get_embedder()

    def retrieve(
        query: str, category: str | None, family_member: str | None
    ) -> list[dict[str, Any]]:
        hits = hybrid_search(db, embedder, query, category=category, family_member=family_member)
        return [asdict(h) for h in hits]

    def fetch_structured(category: str | None, family_member: str | None) -> list[dict[str, Any]]:
        q = db.query(Payment).join(Document)
        if category:
            q = q.filter(Document.category == category)
        if family_member:
            q = q.filter(Document.family_member == family_member)
        return [
            {
                "document_id": p.document_id,
                "document_title": p.document.title,
                "amount": float(p.amount),
                "currency": p.currency,
                "due_date": p.due_date.isoformat() if p.due_date else None,
                "description": p.description,
            }
            for p in q.limit(200).all()
        ]

    def audit(query_id: str, agent: str, payload: dict[str, Any]) -> None:
        db.add(AgentRun(query_id=query_id, agent=agent, payload=payload))
        db.flush()

    return Services(
        llm=get_llm(),
        retrieve=retrieve,
        fetch_structured=fetch_structured,
        audit=audit,
        min_confidence=get_settings().min_confidence,
    )

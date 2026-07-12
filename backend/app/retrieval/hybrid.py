"""Hybrid retrieval: semantic (pgvector) + keyword (FTS) + metadata filters, then rerank."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.llm.embeddings import Embedder
from app.retrieval.reranker import rerank_hits
from app.storage.models import Chunk
from app.storage.vector import keyword_search, semantic_search


@dataclass
class Hit:
    chunk_id: int
    document_id: int
    document_title: str
    page: int | None
    section: str | None
    text: str
    score: float


def hybrid_search(
    db: Session,
    embedder: Embedder,
    query: str,
    category: str | None = None,
    family_member: str | None = None,
    limit: int = 8,
) -> list[Hit]:
    query_embedding = embedder.embed_query(query)
    semantic = semantic_search(
        db, query_embedding, limit=limit * 2, category=category, family_member=family_member
    )
    keyword = keyword_search(db, query, limit=limit * 2, category=category)

    # Merge, keeping the best score per chunk.
    merged: dict[int, tuple[Chunk, float]] = {}
    for chunk, score in [*semantic, *keyword]:
        if chunk.id not in merged or score > merged[chunk.id][1]:
            merged[chunk.id] = (chunk, score)

    hits = [
        Hit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=chunk.document.title,
            page=chunk.page,
            section=chunk.section,
            text=chunk.text,
            score=score,
        )
        for chunk, score in merged.values()
    ]
    return rerank_hits(embedder, query, hits, top_k=limit)

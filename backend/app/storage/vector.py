"""Semantic (pgvector) and keyword (Postgres FTS) search over chunks."""

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.storage.models import Chunk, Document


def semantic_search(
    db: Session,
    query_embedding: list[float],
    limit: int = 10,
    category: str | None = None,
    family_member: str | None = None,
) -> list[tuple[Chunk, float]]:
    q = (
        db.query(Chunk, Chunk.embedding.cosine_distance(query_embedding).label("distance"))
        .join(Document)
        .filter(Chunk.embedding.isnot(None))
    )
    if category:
        q = q.filter(Document.category == category)
    if family_member:
        q = q.filter(Document.family_member == family_member)
    rows = q.order_by(sql_text("distance")).limit(limit).all()
    return [(chunk, 1.0 - dist) for chunk, dist in rows]


def keyword_search(
    db: Session,
    query: str,
    limit: int = 10,
    category: str | None = None,
) -> list[tuple[Chunk, float]]:
    """BM25-style keyword search via Postgres full-text search (russian config)."""
    sql = """
        SELECT c.id, ts_rank(to_tsvector('russian', c.text),
                             plainto_tsquery('russian', :q)) AS rank
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE to_tsvector('russian', c.text) @@ plainto_tsquery('russian', :q)
          AND (:category IS NULL OR d.category = :category)
        ORDER BY rank DESC
        LIMIT :limit
    """
    rows = db.execute(sql_text(sql), {"q": query, "category": category, "limit": limit}).all()
    if not rows:
        return []
    by_id = {c.id: c for c in db.query(Chunk).filter(Chunk.id.in_([r[0] for r in rows])).all()}
    return [(by_id[cid], float(rank)) for cid, rank in rows if cid in by_id]

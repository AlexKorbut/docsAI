"""Cross-encoder reranking via Voyage rerank-2, with graceful passthrough."""

import logging
from typing import TYPE_CHECKING

from app.llm.embeddings import Embedder

if TYPE_CHECKING:
    from app.retrieval.hybrid import Hit

logger = logging.getLogger(__name__)


def rerank_hits(embedder: Embedder, query: str, hits: list["Hit"], top_k: int = 8) -> list["Hit"]:
    if not hits:
        return []
    try:
        ranked = embedder.rerank(query, [h.text for h in hits], top_k=min(top_k, len(hits)))
    except Exception:
        logger.warning("Rerank failed; falling back to retrieval scores", exc_info=True)
        return sorted(hits, key=lambda h: h.score, reverse=True)[:top_k]

    result = []
    for index, score in ranked:
        hit = hits[index]
        hit.score = score
        result.append(hit)
    return result


# TODO: LLM-based rerank fallback (Claude scoring passages) when Voyage is unavailable.

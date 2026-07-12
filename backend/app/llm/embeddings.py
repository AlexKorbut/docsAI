"""Voyage AI embeddings and reranking."""

from functools import lru_cache

import voyageai

from app.config import get_settings


class Embedder:
    def __init__(self) -> None:
        s = get_settings()
        self._client = voyageai.Client(api_key=s.voyage_api_key)
        self._model = s.embedding_model
        self._rerank_model = s.rerank_model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._client.embed(texts, model=self._model, input_type="document").embeddings

    def embed_query(self, text: str) -> list[float]:
        return self._client.embed([text], model=self._model, input_type="query").embeddings[0]

    def rerank(self, query: str, documents: list[str], top_k: int = 8) -> list[tuple[int, float]]:
        """Return (original_index, relevance_score) sorted by relevance."""
        result = self._client.rerank(query, documents, model=self._rerank_model, top_k=top_k)
        return [(r.index, r.relevance_score) for r in result.results]


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()

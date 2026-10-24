"""Turns a question into the most relevant document chunks."""

from __future__ import annotations

from typing import Protocol

from src.capabilities.rag.store import SearchResult, VectorStore

# nomic-embed-text is trained with these task prefixes; using them
# noticeably improves retrieval quality.
QUERY_PREFIX = "search_query: "
DOCUMENT_PREFIX = "search_document: "


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class Retriever:
    def __init__(self, embedder: Embedder, store: VectorStore, top_k: int, min_similarity: float):
        self.embedder = embedder
        self.store = store
        self.top_k = top_k
        self.min_similarity = min_similarity

    def retrieve(self, query: str) -> list[SearchResult]:
        """Return the top-k chunks whose similarity is above the threshold."""
        [vector] = self.embedder.embed([QUERY_PREFIX + query])
        results = self.store.search(vector, self.top_k)
        return [r for r in results if r.score >= self.min_similarity]

    def retrieve_all_scores(self, query: str) -> list[SearchResult]:
        """Top-k results without the threshold (used by evaluation/debugging)."""
        [vector] = self.embedder.embed([QUERY_PREFIX + query])
        return self.store.search(vector, self.top_k)

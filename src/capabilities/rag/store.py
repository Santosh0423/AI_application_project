"""A small file-based vector store using NumPy cosine similarity.

The knowledge base is a few hundred chunks, so an exact in-memory search
is fast (milliseconds) and avoids running a separate database server.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.capabilities.rag.documents import Chunk


class IndexNotFoundError(Exception):
    user_message = "The knowledge base has not been built yet. Run: python scripts/ingest.py"


@dataclass
class SearchResult:
    chunk: Chunk
    score: float


class VectorStore:
    VECTORS_FILE = "vectors.npy"
    CHUNKS_FILE = "chunks.json"

    def __init__(self, chunks: list[Chunk], vectors: np.ndarray, embed_model: str = ""):
        if len(chunks) != len(vectors):
            raise ValueError("Number of chunks and vectors must match")
        self.chunks = chunks
        self.embed_model = embed_model
        self.vectors = _normalize(np.asarray(vectors, dtype=np.float32))

    def __len__(self) -> int:
        return len(self.chunks)

    def search(self, query_vector: list[float], k: int) -> list[SearchResult]:
        if not self.chunks:
            return []
        query = _normalize(np.asarray([query_vector], dtype=np.float32))[0]
        scores = self.vectors @ query
        top = np.argsort(-scores)[:k]
        return [SearchResult(self.chunks[i], float(scores[i])) for i in top]

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / self.VECTORS_FILE, self.vectors)
        meta = {"embed_model": self.embed_model, "chunks": [c.to_dict() for c in self.chunks]}
        (directory / self.CHUNKS_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, directory: Path) -> "VectorStore":
        vectors_path = directory / cls.VECTORS_FILE
        chunks_path = directory / cls.CHUNKS_FILE
        if not vectors_path.exists() or not chunks_path.exists():
            raise IndexNotFoundError(f"No index in {directory}")
        meta = json.loads(chunks_path.read_text(encoding="utf-8"))
        chunks = [Chunk(**c) for c in meta["chunks"]]
        return cls(chunks, np.load(vectors_path), embed_model=meta.get("embed_model", ""))


def _normalize(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms

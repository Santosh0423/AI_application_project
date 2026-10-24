"""Build the vector index from the documents in data/raw."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.config import Settings
from src.capabilities.rag.documents import chunk_documents, load_documents
from src.capabilities.rag.retriever import DOCUMENT_PREFIX, Embedder
from src.capabilities.rag.store import VectorStore

BATCH_SIZE = 16


@dataclass
class IngestStats:
    documents: int
    chunks: int


def build_index(settings: Settings, embedder: Embedder, progress=print) -> IngestStats:
    docs = load_documents(settings.raw_dir)
    if not docs:
        raise RuntimeError(
            f"No documents found in {settings.raw_dir}. Run `python scripts/fetch_sources.py` first."
        )
    chunks = chunk_documents(docs, settings.chunk_size, settings.chunk_overlap)
    progress(f"Loaded {len(docs)} documents -> {len(chunks)} chunks")

    vectors: list[list[float]] = []
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        # Include the title so short chunks keep their topic.
        texts = [f"{DOCUMENT_PREFIX}{c.title}\n{c.text}" for c in batch]
        vectors.extend(embedder.embed(texts))
        progress(f"  embedded {min(start + BATCH_SIZE, len(chunks))}/{len(chunks)}")

    store = VectorStore(chunks, np.asarray(vectors), embed_model=settings.embed_model)
    store.save(settings.index_dir)
    progress(f"Index saved to {settings.index_dir}")
    return IngestStats(documents=len(docs), chunks=len(chunks))

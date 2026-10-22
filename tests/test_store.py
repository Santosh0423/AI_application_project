import numpy as np
import pytest

from src.capabilities.rag.documents import Chunk
from src.capabilities.rag.retriever import Retriever
from src.capabilities.rag.store import IndexNotFoundError, VectorStore


def make_chunk(i: int) -> Chunk:
    return Chunk(id=str(i), text=f"text {i}", title=f"T{i}", url=f"https://x/{i}", authority="Migri", retrieved="")


@pytest.fixture
def store():
    vectors = np.array([[1, 0, 0], [0, 1, 0], [0.9, 0.1, 0]], dtype=np.float32)
    return VectorStore([make_chunk(i) for i in range(3)], vectors, embed_model="test")


def test_search_returns_most_similar_first(store):
    results = store.search([1, 0, 0], k=2)
    assert [r.chunk.id for r in results] == ["0", "2"]
    assert results[0].score == pytest.approx(1.0)


def test_save_and_load_roundtrip(store, tmp_path):
    store.save(tmp_path)
    loaded = VectorStore.load(tmp_path)
    assert len(loaded) == 3
    assert loaded.embed_model == "test"
    assert loaded.search([0, 1, 0], k=1)[0].chunk.id == "1"


def test_load_missing_index_raises(tmp_path):
    with pytest.raises(IndexNotFoundError):
        VectorStore.load(tmp_path / "nothing")


class FakeEmbedder:
    def __init__(self, vector):
        self.vector = vector
        self.calls = []

    def embed(self, texts):
        self.calls.append(texts)
        return [self.vector for _ in texts]


def test_retriever_applies_threshold_and_query_prefix(store):
    embedder = FakeEmbedder([1, 0, 0])
    retriever = Retriever(embedder, store, top_k=3, min_similarity=0.5)
    results = retriever.retrieve("work hours")
    assert [r.chunk.id for r in results] == ["0", "2"]  # chunk 1 is orthogonal -> filtered out
    assert embedder.calls[0][0].startswith("search_query: ")

import pytest
import requests

from src.models.model_client import ModelResponseError, OllamaConnectionError, ModelNotFoundError, OllamaModelClient


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


@pytest.fixture
def client():
    return OllamaModelClient("http://localhost:11434", "qwen2.5:7b", "nomic-embed-text", timeout=5, retries=0)


def test_chat_returns_content(monkeypatch, client):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(payload={"message": {"content": " Hi "}}))
    assert client.chat([{"role": "user", "content": "hi"}]) == "Hi"


def test_chat_connection_error(monkeypatch, client):
    def boom(*a, **k):
        raise requests.ConnectionError("refused")
    monkeypatch.setattr(requests, "post", boom)
    with pytest.raises(OllamaConnectionError):
        client.chat([])


def test_model_not_found(monkeypatch, client):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(404, text="model not found"))
    with pytest.raises(ModelNotFoundError) as exc:
        client.chat([])
    assert "ollama pull qwen2.5:7b" in exc.value.user_message


def test_empty_chat_response_is_rejected(monkeypatch, client):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(payload={"message": {"content": ""}}))
    with pytest.raises(ModelResponseError):
        client.chat([])


def test_embed_checks_vector_count(monkeypatch, client):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(payload={"embeddings": [[0.1]]}))
    with pytest.raises(ModelResponseError):
        client.embed(["a", "b"])

"""Reusable client for the Ollama HTTP API (chat + embeddings).

All model access in the application goes through this module, so the rest
of the code never deals with HTTP details or raw Ollama errors.
"""

from __future__ import annotations

import time
from typing import Iterable

import requests


class ModelClientError(Exception):
    """Base class for model errors. `user_message` is safe to show in the UI."""

    user_message = "The AI model failed to respond. Please try again."


class OllamaConnectionError(ModelClientError):
    user_message = (
        "The AI model is not reachable. Make sure Ollama is installed and running "
        "(start the Ollama app or run `ollama serve`)."
    )


class ModelTimeoutError(ModelClientError):
    user_message = "The AI model took too long to answer. Please try again or ask a shorter question."


class ModelNotFoundError(ModelClientError):
    def __init__(self, model: str):
        super().__init__(f"Model not found: {model}")
        self.model = model
        self.user_message = f"The model '{model}' is not downloaded. Run: ollama pull {model}"


class ModelResponseError(ModelClientError):
    user_message = "The AI model returned an unexpected response. Please try again."


class OllamaModelClient:
    def __init__(
        self,
        base_url: str,
        chat_model: str,
        embed_model: str,
        timeout: int = 300,
        temperature: float = 0.1,
        retries: int = 1,
    ):
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.timeout = timeout
        self.temperature = temperature
        self.retries = retries

    # ------------------------------------------------------------------ public

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send chat messages and return the assistant's text."""
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        data = self._post("/api/chat", payload, model=self.chat_model)
        content = (data.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ModelResponseError("Empty or malformed chat response")
        return content.strip()

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        texts = list(texts)
        if not texts:
            return []
        data = self._post("/api/embed", {"model": self.embed_model, "input": texts}, model=self.embed_model)
        vectors = data.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise ModelResponseError("Malformed embedding response")
        return vectors

    def missing_models(self) -> list[str]:
        """Return required models that are not downloaded. Raises if Ollama is down."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaConnectionError(str(exc)) from exc
        installed = {m.get("name", "") for m in resp.json().get("models", [])}
        # "nomic-embed-text" is installed as "nomic-embed-text:latest"
        installed |= {name.removesuffix(":latest") for name in installed}
        return [m for m in (self.chat_model, self.embed_model) if m not in installed]

    # ----------------------------------------------------------------- private

    def _post(self, path: str, payload: dict, model: str) -> dict:
        last_error: ModelClientError | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = requests.post(f"{self.base_url}{path}", json=payload, timeout=self.timeout)
            except requests.ConnectionError as exc:
                last_error = OllamaConnectionError(str(exc))
            except requests.Timeout as exc:
                # A timeout is unlikely to succeed on retry; fail fast.
                raise ModelTimeoutError(str(exc)) from exc
            else:
                if resp.status_code == 404:
                    raise ModelNotFoundError(model)
                if resp.status_code >= 500:
                    last_error = ModelResponseError(f"Ollama server error {resp.status_code}: {resp.text[:200]}")
                elif resp.status_code >= 400:
                    raise ModelResponseError(f"Ollama error {resp.status_code}: {resp.text[:200]}")
                else:
                    try:
                        return resp.json()
                    except ValueError as exc:
                        raise ModelResponseError("Response was not valid JSON") from exc
            if attempt < self.retries:
                time.sleep(1)
        assert last_error is not None
        raise last_error

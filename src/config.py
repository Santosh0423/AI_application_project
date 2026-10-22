"""Application settings loaded from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Setting {name} must be an integer, got {value!r}") from exc


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Setting {name} must be a number, got {value!r}") from exc


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    model_name: str
    embed_model: str
    request_timeout: int
    llm_temperature: float

    chunk_size: int
    chunk_overlap: int
    top_k: int
    min_similarity: float
    max_question_chars: int
    history_turns: int

    raw_dir: Path
    index_dir: Path
    profile_path: Path
    sources_path: Path

    server_host: str
    server_port: int


def load_settings() -> Settings:
    """Read settings from the environment (and .env if present)."""
    load_dotenv(PROJECT_ROOT / ".env")

    data_dir = PROJECT_ROOT / "data"
    settings = Settings(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        model_name=os.getenv("MODEL_NAME", "qwen2.5:7b"),
        embed_model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
        request_timeout=_get_int("REQUEST_TIMEOUT", 300),
        llm_temperature=_get_float("LLM_TEMPERATURE", 0.1),
        chunk_size=_get_int("CHUNK_SIZE", 900),
        chunk_overlap=_get_int("CHUNK_OVERLAP", 150),
        top_k=_get_int("TOP_K", 4),
        min_similarity=_get_float("MIN_SIMILARITY", 0.60),
        max_question_chars=_get_int("MAX_QUESTION_CHARS", 500),
        history_turns=_get_int("HISTORY_TURNS", 2),
        raw_dir=data_dir / "raw",
        index_dir=data_dir / "index",
        profile_path=data_dir / "profile.json",
        sources_path=data_dir / "sources.json",
        server_host=os.getenv("SERVER_HOST", "127.0.0.1"),
        server_port=_get_int("SERVER_PORT", 7860),
    )

    if settings.chunk_overlap >= settings.chunk_size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
    if settings.top_k < 1:
        raise ValueError("TOP_K must be at least 1")
    return settings

import pytest

from src.config import load_settings


def test_default_settings_load(monkeypatch):
    for name in ("MODEL_NAME", "EMBED_MODEL", "TOP_K", "MIN_SIMILARITY"):
        monkeypatch.delenv(name, raising=False)
    settings = load_settings()
    assert settings.ollama_base_url.startswith("http")
    assert settings.model_name
    assert settings.top_k >= 1
    assert 0 < settings.min_similarity < 1


def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "llama3.2:3b")
    monkeypatch.setenv("TOP_K", "3")
    settings = load_settings()
    assert settings.model_name == "llama3.2:3b"
    assert settings.top_k == 3


def test_invalid_number_is_reported(monkeypatch):
    monkeypatch.setenv("TOP_K", "four")
    with pytest.raises(ValueError, match="TOP_K"):
        load_settings()


def test_overlap_must_be_smaller_than_chunk(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "100")
    monkeypatch.setenv("CHUNK_OVERLAP", "100")
    with pytest.raises(ValueError, match="CHUNK_OVERLAP"):
        load_settings()

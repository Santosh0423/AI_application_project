"""Build the knowledge base (vector index) from data/raw.

Usage:  python scripts/ingest.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_settings  # noqa: E402
from src.models.model_client import ModelClientError, OllamaModelClient  # noqa: E402
from src.capabilities.rag.ingest import build_index  # noqa: E402


def main() -> int:
    settings = load_settings()
    client = OllamaModelClient(settings.ollama_base_url, settings.model_name, settings.embed_model,
                          timeout=settings.request_timeout)
    try:
        stats = build_index(settings, client)
    except ModelClientError as exc:
        print(f"ERROR: {exc.user_message}\n({exc})")
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Done: {stats.documents} documents, {stats.chunks} chunks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

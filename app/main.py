"""Entry point: wires the components together and starts the web UI.

Run with:  python -m app.main
"""

from __future__ import annotations

import logging

from src.config import Settings, load_settings
from src.models.model_client import ModelClientError, OllamaModelClient
from src.capabilities.rag.retriever import Retriever
from src.capabilities.rag.store import IndexNotFoundError, VectorStore
from src.services.ai_service import AIService
from src.capabilities.memory import ProfileStore
from app.ui import build_ui

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")


def system_status(client: OllamaModelClient, store: VectorStore | None, settings: Settings) -> str:
    lines = []
    try:
        missing = client.missing_models()
        if missing:
            lines += [f"Problem: missing model `{m}` – run `ollama pull {m}`" for m in missing]
        else:
            lines.append(f"OK: Ollama running (`{settings.model_name}`)")
    except ModelClientError as exc:
        lines.append(f"Problem: {exc.user_message}")
    if store is None:
        lines.append(f"Problem: {IndexNotFoundError.user_message}")
    else:
        lines.append(f"OK: Knowledge base: {len(store)} passages")
        if store.embed_model and store.embed_model != settings.embed_model:
            lines.append(f"Warning: index was built with `{store.embed_model}`; re-run ingestion.")
    return "\n\n".join(lines)


def main() -> None:
    settings = load_settings()
    client = OllamaModelClient(
        settings.ollama_base_url,
        settings.model_name,
        settings.embed_model,
        timeout=settings.request_timeout,
        temperature=settings.llm_temperature,
    )

    try:
        store: VectorStore | None = VectorStore.load(settings.index_dir)
        retriever = Retriever(client, store, settings.top_k, settings.min_similarity)
    except IndexNotFoundError:
        logger.warning(IndexNotFoundError.user_message)
        store, retriever = None, None

    assistant = AIService(retriever, client, settings.max_question_chars, settings.history_turns)
    status_text = system_status(client, store, settings)
    logger.info("Startup status:\n%s", status_text)

    demo = build_ui(assistant, ProfileStore(settings.profile_path), lambda: system_status(client, store, settings))
    demo.launch(server_name=settings.server_host, server_port=settings.server_port)


if __name__ == "__main__":
    main()

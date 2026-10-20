"""Core application logic: validate -> retrieve -> prompt -> call model -> validate.

This module has no UI code, so it can be used by the Gradio app, the
evaluation script and the tests in exactly the same way.
"""

from __future__ import annotations

import logging
import re
from typing import Protocol

from src.capabilities.memory import UserProfile
from src.capabilities.rag.store import IndexNotFoundError, SearchResult
from src.models.model_client import ModelClientError
from src.schemas.responses import AIResponse, Source

logger = logging.getLogger(__name__)

NOT_FOUND_TOKEN = "NOT_FOUND"

SYSTEM_PROMPT = f"""You are "Finland Bureaucracy Helper", an assistant for international students in Finland.
You help with residence permits, registration (DVV), Kela, taxes, working rights and similar official matters.

Rules:
1. Answer ONLY with information from the numbered CONTEXT passages. Never use outside knowledge.
2. After every fact, cite the passage number in square brackets, e.g. [1] or [2][3].
3. If the CONTEXT does not contain the answer, or the question is not about living, studying or
   working in Finland, reply with exactly: {NOT_FOUND_TOKEN}
4. Use the USER PROFILE to tailor the answer. If the answer depends on something the profile does not
   say (for example EU vs non-EU), briefly explain each case.
5. Write in plain, simple English. Use short bullet points or numbered steps. Maximum about 200 words.
6. Do not promise outcomes and do not give legal advice. Do not invent deadlines, fees or numbers."""

NOT_FOUND_MESSAGE = (
    "I couldn't find reliable information about this in my official sources, so I won't guess.\n\n"
    "You can check directly with:\n"
    "- **Migri** (residence permits): https://migri.fi/en\n"
    "- **DVV** (registration, personal identity code): https://dvv.fi/en\n"
    "- **Kela** (social security): https://www.kela.fi/web/en\n"
    "- **Vero** (tax card, taxes): https://www.vero.fi/en\n"
    "- **InfoFinland** (general guidance): https://www.infofinland.fi/en\n"
    "- Your university's international services"
)

_CITATION = re.compile(r"\[(\d+)\]")


class RetrieverLike(Protocol):
    def retrieve(self, query: str) -> list[SearchResult]: ...


class ChatModel(Protocol):
    def generate(self, prompt: str) -> str: ...

class AIService:
    """Application service layer: the UI talks only to this class, never to Ollama directly."""

    def __init__(
        self,
        retriever: RetrieverLike | None,
        model: ChatModel,
        max_question_chars: int = 500,
        history_turns: int = 2,
    ):
        self.retriever = retriever
        self.model = model
        self.max_question_chars = max_question_chars
        self.history_turns = history_turns

    def answer(
        self,
        question: str,
        profile: UserProfile | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> AIResponse:
        profile = profile or UserProfile()
        history = history or []
        question = (question or "").strip()

        # 1. Validate input
        if not question:
            return AIResponse(answer="Please type a question.", status="invalid_input")
        if len(question) > self.max_question_chars:
            return AIResponse(
                answer=f"Your question is too long ({len(question)} characters). "
                f"Please keep it under {self.max_question_chars} characters.",
                status="invalid_input",
            )
        if self.retriever is None:
            return AIResponse(answer=IndexNotFoundError.user_message, status="error")

        # 2. Retrieve evidence
        try:
            results = self.retriever.retrieve(self._retrieval_query(question, history))
        except ModelClientError as exc:
            logger.error("Retrieval failed: %s", exc)
            return AIResponse(answer=exc.user_message, status="error")
        if not results:
            return AIResponse(answer=NOT_FOUND_MESSAGE, status="not_found")

        # 3. Generate
        messages = self._build_messages(question, profile, history, results)
        try:
            raw = self.model.chat(messages)
        except ModelClientError as exc:
            logger.error("Generation failed: %s", exc)
            return AIResponse(answer=exc.user_message, status="error", retrieved=results)

        # 4. Validate output
        return self._postprocess(raw, results)

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _retrieval_query(question: str, history: list[tuple[str, str]]) -> str:
        # Short follow-ups ("how long does it take?") need the previous question for context.
        if history and len(question.split()) <= 6:
            return f"{history[-1][0]} {question}"
        return question

    def _build_messages(
        self,
        question: str,
        profile: UserProfile,
        history: list[tuple[str, str]],
        results: list[SearchResult],
    ) -> list[dict[str, str]]:
        context = "\n\n".join(
            f"[{i}] ({r.chunk.authority} – {r.chunk.title})\n{r.chunk.text}"
            for i, r in enumerate(results, start=1)
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for user_msg, bot_msg in history[-self.history_turns:] if self.history_turns else []:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": bot_msg})
        messages.append(
            {
                "role": "user",
                "content": f"USER PROFILE: {profile.describe()}\n\nCONTEXT:\n{context}\n\nQUESTION: {question}",
            }
        )
        return messages

    @staticmethod
    def _postprocess(raw: str, results: list[SearchResult]) -> AIResponse:
        text = raw.strip()
        if text.upper().startswith(NOT_FOUND_TOKEN) or (NOT_FOUND_TOKEN in text and len(text) < 80):
            return AIResponse(answer=NOT_FOUND_MESSAGE, status="not_found", retrieved=results)

        cited = [int(n) for n in _CITATION.findall(text)]
        valid = sorted({n for n in cited if 1 <= n <= len(results)})

        # Remove citation numbers that point to passages that don't exist.
        text = _CITATION.sub(lambda m: m.group(0) if 1 <= int(m.group(1)) <= len(results) else "", text)

        used = [results[n - 1] for n in valid] if valid else results

        # One source per page; passages from the same page share a number.
        sources: list[Source] = []
        source_index: dict[str, int] = {}
        for r in used:
            key = r.chunk.url or r.chunk.title
            if key not in source_index:
                sources.append(
                    Source(title=r.chunk.title, url=r.chunk.url, authority=r.chunk.authority, retrieved=r.chunk.retrieved)
                )
                source_index[key] = len(sources)

        if valid:
            # Renumber citations so they match the Sources list, and merge repeats like [1][1].
            def renumber(m: re.Match) -> str:
                chunk = results[int(m.group(1)) - 1].chunk
                return f"[{source_index[chunk.url or chunk.title]}]"

            text = _CITATION.sub(renumber, text)
            text = re.sub(r"(\[\d+\])(\1)+", r"\1", text)
        else:
            text += "\n\n_Note: the model did not cite specific passages; the sources below were used as context._"
        return AIResponse(
            answer=text, status="answered", sources=sources, retrieved=results, cited_correctly=bool(valid)
        )

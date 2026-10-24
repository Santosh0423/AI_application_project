"""Structured, validated objects passed from the service layer to the UI and evaluation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DISCLAIMER = "_General guidance only, not legal advice. Always confirm with the official authority._"

Status = Literal["answered", "not_found", "invalid_input", "error"]


class Source(BaseModel):
    """An official page that an answer is based on."""

    title: str
    url: str = ""
    authority: str = "Unknown"
    retrieved: str = Field("", description="Date the page was downloaded (YYYY-MM-DD).")


class AIResponse(BaseModel):
    """Result of one question, returned by the AI service."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    answer: str = Field(..., description="Answer text, or a user-friendly refusal/error message.")
    status: Status = Field(..., description="What happened: answered, not_found, invalid_input or error.")
    sources: list[Source] = Field(default_factory=list, description="Pages cited in the answer.")
    retrieved: list[Any] = Field(default_factory=list, description="Retrieved passages (SearchResult) used as context.")
    cited_correctly: bool = Field(False, description="True if the model cited at least one valid passage.")

    @property
    def success(self) -> bool:
        return self.status == "answered"

    def to_markdown(self) -> str:
        """Answer formatted for the chat window, including sources."""
        if self.status != "answered":
            return self.answer
        lines = [self.answer, "", "**Sources**"]
        for i, s in enumerate(self.sources, start=1):
            label = f"{s.authority} – {s.title}"
            lines.append(f"{i}. [{label}]({s.url})" if s.url else f"{i}. {label}")
        lines += ["", DISCLAIMER]
        return "\n".join(lines)

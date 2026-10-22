"""Loading source documents and splitting them into chunks."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Document:
    title: str
    url: str
    authority: str
    retrieved: str
    text: str
    path: str = ""


@dataclass
class Chunk:
    id: str
    text: str
    title: str
    url: str
    authority: str
    retrieved: str

    def to_dict(self) -> dict:
        return asdict(self)


_FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_document(raw: str, path: str = "") -> Document:
    """Parse a document with a simple `key: value` front-matter header."""
    meta: dict[str, str] = {}
    body = raw
    match = _FRONT_MATTER.match(raw)
    if match:
        for line in match.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip().lower()] = value.strip()
        body = raw[match.end():]
    return Document(
        title=meta.get("title") or Path(path).stem or "Untitled",
        url=meta.get("url", ""),
        authority=meta.get("authority", "Unknown"),
        retrieved=meta.get("retrieved", ""),
        text=body.strip(),
        path=path,
    )


def load_documents(raw_dir: Path) -> list[Document]:
    docs = []
    for path in sorted(raw_dir.glob("*.md")) + sorted(raw_dir.glob("*.txt")):
        doc = parse_document(path.read_text(encoding="utf-8"), path=str(path))
        if doc.text:
            docs.append(doc)
    return docs


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into chunks of about `chunk_size` characters.

    Paragraphs are kept together where possible so a chunk does not cut a
    rule in half. Consecutive chunks share `overlap` characters of context.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            pieces.append(para)
        else:
            pieces.extend(_split_long(para, chunk_size))

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            # Start the overlap at a word boundary.
            tail = tail[tail.find(" ") + 1:] if " " in tail else tail
            current = f"{tail}\n\n{piece}" if tail else piece
            if len(current) > chunk_size:
                current = piece
        else:
            current = piece
    if current:
        chunks.append(current)
    return chunks


def _split_long(paragraph: str, chunk_size: int) -> list[str]:
    """Split a long paragraph on sentence boundaries (or hard-cut as last resort)."""
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    parts: list[str] = []
    current = ""
    for sentence in sentences:
        while len(sentence) > chunk_size:
            if current:
                parts.append(current)
                current = ""
            parts.append(sentence[:chunk_size])
            sentence = sentence[chunk_size:]
        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            parts.append(current)
            current = sentence
    if current:
        parts.append(current)
    return parts


def chunk_documents(docs: list[Document], chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc_index, doc in enumerate(docs):
        for i, text in enumerate(chunk_text(doc.text, chunk_size, overlap)):
            chunks.append(
                Chunk(
                    id=f"{doc_index}-{i}",
                    text=text,
                    title=doc.title,
                    url=doc.url,
                    authority=doc.authority,
                    retrieved=doc.retrieved,
                )
            )
    return chunks

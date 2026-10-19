from src.capabilities.rag.documents import chunk_documents, chunk_text, load_documents, parse_document

DOC = """---
title: Working during studies
url: https://migri.fi/en/example
authority: Migri
retrieved: 2026-10-17
---

## Working

Students may work 30 hours per week on average.
"""


def test_parse_document_reads_front_matter():
    doc = parse_document(DOC)
    assert doc.title == "Working during studies"
    assert doc.url == "https://migri.fi/en/example"
    assert doc.authority == "Migri"
    assert doc.text.startswith("## Working")


def test_parse_document_without_front_matter_uses_file_name():
    doc = parse_document("Just text", path="data/raw/kela-card.md")
    assert doc.title == "kela-card"
    assert doc.text == "Just text"


def test_chunks_respect_size_limit():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 40 for i in range(30))
    chunks = chunk_text(text, chunk_size=500, overlap=80)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


def test_long_paragraph_is_split():
    text = "This is a sentence. " * 200
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert all(len(c) <= 300 for c in chunks)
    assert "".join(chunks).count("sentence") >= 200


def test_short_text_is_single_chunk():
    assert chunk_text("Short text.", 500, 50) == ["Short text."]


def test_chunk_metadata_is_kept(tmp_path):
    (tmp_path / "a.md").write_text(DOC, encoding="utf-8")
    (tmp_path / "empty.md").write_text("", encoding="utf-8")
    docs = load_documents(tmp_path)
    assert len(docs) == 1
    chunks = chunk_documents(docs, 500, 50)
    assert chunks[0].url == "https://migri.fi/en/example"
    assert chunks[0].authority == "Migri"

# Project decisions

## Decision 1 — Model selection

**Decision:** `qwen2.5:7b` for answers and `nomic-embed-text` for embeddings, both running locally in Ollama. `llama3.2:3b` is a configurable fallback (`MODEL_NAME` in `.env`) for laptops with 8 GB RAM.

**Alternatives considered:** `llama3.2:3b` (the template default), hosted APIs (OpenAI, Groq).

**Why we chose this:** The 7B model follows our strict rules (answer only from context, cite `[n]`, reply `NOT_FOUND`) more reliably than 3B models. Local inference is free, needs no API keys that could leak, and keeps students' personal immigration questions on their own computer. Temperature is 0.1, because factual consistency matters more than creativity. *Trade-off:* without a GPU, an answer takes about 1 minute.

---

## Decision 2 — Additional AI capability

**Decision:** **RAG** over 33 official pages (Migri, DVV, Kela, Vero, InfoFinland), plus **persistent memory** of the user's profile.

**Why it is needed:** The core problem is *finding and correctly using* official rules. A plain chatbot can invent rules, which could harm a student. RAG grounds every answer in official text and shows citations the user can verify. Many rules depend on the user's situation (EU citizens register their right of residence, non-EU students need a residence permit), so the saved profile is added to every prompt.

**Alternatives considered:**
- *Agent / MCP with live web browsing:* rejected. The steps are always the same (retrieve, then answer), so an agent adds latency and unpredictability, and live browsing would bypass our verified sources.
- *Long chat memory:* rejected in favour of a small structured profile plus the last 2 turns. Long history makes prompts slower and brings in irrelevant context.

---

## Decision 3 — Architecture

**Decision:** We kept the template's layers (UI → service → model client) and added the capabilities under `src/capabilities/`. The UI never calls the model directly.

**Why:** It keeps the logic testable without Ollama (the service depends on `retrieve()`/`chat()` protocols, so tests use fakes) and lets the evaluation script use exactly the same service as the UI.

---

## Decision 4 — NumPy vector store instead of ChromaDB/FAISS

**Decision:** Store embeddings in a `.npy` file and do an exact cosine search.

**Why:** About 400 chunks, so an exact search takes milliseconds. No extra database server, works on any Python version, and is easy to explain and test. With tens of thousands of documents we would switch to a vector database.

---

## Decision 5 — Two-layer refusal and threshold tuning

**Decision:** (1) If no passage reaches `MIN_SIMILARITY`, refuse without calling the model. (2) Otherwise the model must reply `NOT_FOUND` when the context doesn't contain the answer.

**Why:** Layer 1 is cheap and deterministic for off-topic questions (refusal in about 2 s instead of about 60 s). Layer 2 catches in-scope questions the documents don't cover.

**Tuning:** We started with 0.55. Measured best-match scores: off-topic about 0.54 ("capital of France", "poem about winter"), on-topic 0.80–0.88, related but not covered (starting a business as a student) about 0.65. We raised the threshold to **0.60** for a safer margin. The business question still reaches the model, which correctly answers `NOT_FOUND`.

---

## Decision 6 — Validating the model's output

**Decision:** Parse `[n]` citations, drop numbers that don't exist, merge passages from the same page into one source, renumber, add a note if nothing was cited, and return a validated Pydantic `AIResponse`.

**Why:** The source list shown to the user must always match real documents, even when the model makes formatting mistakes.

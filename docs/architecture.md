# Architecture

## Components

```mermaid
flowchart LR
    U[Student] --> UI["Gradio UI<br/>app/ui.py"]
    UI --> S["AI service<br/>src/services/ai_service.py<br/>validate → retrieve → prompt → validate"]
    UI --> M["Profile memory<br/>src/capabilities/memory.py"]
    S --> M
    S --> R["Retriever<br/>src/capabilities/rag/retriever.py"]
    R --> V[("Vector index<br/>data/index/")]
    R --> C
    S --> C["Model client<br/>src/models/model_client.py"]
    S --> SC["Response schemas<br/>src/schemas/responses.py"]
    C --> O["Ollama<br/>qwen2.5:7b + nomic-embed-text"]

    subgraph Offline["Offline: build the knowledge base"]
      J["data/sources.json"] --> F["scripts/fetch_sources.py"]
      F --> D["data/raw/*.md"]
      D --> I["scripts/ingest.py<br/>src/capabilities/rag/ingest.py"]
      I --> V
    end
```

The template's core rule is kept: **the UI never talks to Ollama or the model client directly.** Everything goes through `AIService`.

| Layer | Files | Responsibility |
|---|---|---|
| Presentation | `app/ui.py`, `app/main.py` | Chat, profile form, system status; `main.py` wires the components together |
| Service | `src/services/ai_service.py` | Input validation, retrieval, prompt building, output validation, error handling |
| Schemas | `src/schemas/responses.py` | Pydantic `AIResponse` and `Source`: validated, structured output |
| Model access | `src/models/model_client.py` | The only code that talks to Ollama: chat + embeddings, timeouts, retry, typed errors |
| Capability: RAG | `src/capabilities/rag/` | Load and chunk documents, vector store, top-k retrieval, index building |
| Capability: memory | `src/capabilities/memory.py` | Persistent user profile with value validation |
| Config | `src/config.py`, `.env` | All settings in one place |

## Request flow (one question)

```mermaid
sequenceDiagram
    participant U as Student
    participant UI as Gradio UI
    participant S as AIService
    participant R as Retriever
    participant O as Ollama

    U->>UI: question + profile
    UI->>S: answer(question, profile, history)
    S->>S: validate input
    S->>R: retrieve(query)
    R->>O: embed("search_query: ...")
    O-->>R: vector
    R-->>S: top-k passages above MIN_SIMILARITY
    alt no relevant passages
        S-->>UI: refusal + links to authorities (no model call)
    else passages found
        S->>O: chat(system rules + profile + numbered passages + question)
        O-->>S: answer with [n] citations, or NOT_FOUND
        S->>S: validate output (citations, NOT_FOUND)
        S-->>UI: AIResponse (answer + sources)
    end
    UI-->>U: answer, sources, disclaimer
```

## Offline ingestion
1. `scripts/fetch_sources.py` downloads each URL in `data/sources.json`, keeps the main content (headings, paragraphs, lists), removes menus, footers and cookie banners, and saves `data/raw/<authority>-<title>.md` with a header holding the title, URL, authority and date.
2. `scripts/ingest.py` splits each document into chunks of about 900 characters (paragraph-aware, 150-character overlap), embeds them with `nomic-embed-text` (title + text, `search_document:` prefix), and saves `data/index/vectors.npy` plus `chunks.json`.

## Testability
`AIService` depends on *protocols* (anything with `retrieve()` / `chat()`), so the unit tests use fakes and run without Ollama.

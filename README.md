# StudyBuddy – AI Study Assistant for Course Materials

This is documentation for the **Development of AI Applications** course final group project.

## Team members

- Santosh Sigdel (santosh23000@student.hamk.fi, santosh.sigdel900@gmail.com)
- Puran karki (amk1002351@student.hamk.fi)
- Manoj Bhattarai (amk1006124@student.hamk.fi)
- Nabin Yari (amk1004480@student.hamk.fi)

## Problem

### Intended users
UAS students who study from many lecture slides for examples PDFs and notes and who are preparing for assignments or projects and exams.

### Problem statement
Course materials are spread into many long files, when students have a question, they have to search through dozens of pages by themself. General chatbots doesn't know the specific course content, can give answers that don't match what lecturer taught.
StudyBuddy lets students ask questions abour their own course materials and get answer also everything runs locally, so the files stay on student's computer.

### Why AI is appropriate
Students ask questions in free-form natural language, keyword can't reliably match those questions to right content.
Answer must be summarized and explained in simple language, not only returned as raw text.
The same question can be asked in a different way, and the answer is often spread across several pages. Language model can combine all this pieces into a clear answer.
Traditional software can be store and search files, but it can't understand or explain their content.

## 4. proposed solution and main workflow
## Main workflow
1. The user (optionally) sets a **profile**: citizenship group (EU/EEA or non-EU), status (degree student or exchange student), city.
2. The user asks a question, e.g. _"Can I work while studying and how many hours?"_
3. The application **retrieves** the most relevant passages from the official document collection.
4. The model generates a **short, plain-language answer** using **only** those passages and the user's profile.
5. The answer is shown with **source citations** (document name + link).
6. If the documents don't contain the answer, the assistant **says so** and points to the right authority instead of guessing.
## Architecture

Full details and the data flow are in [`docs/architecture.md`](docs/architecture.md), and the design decisions are in [`docs/project-decisions.md`](docs/project-decisions.md).

```text
User
  ↓
Gradio UI (app/ui.py)
  ↓
Application / AI Service (src/services/ai_service.py)
  ├──→ RAG capability (src/capabilities/rag.py)
  │       document loading, chunking, NumPy vector store (data/index/)
  ↓
Model Client (src/models/model_client.py)
  ↓
Ollama (Local LLM Server: llama3.2 + nomic-embed-text)
```

## Project structure
```text
app/
  main.py                  entry point (python -m app.main)
  ui.py                    Gradio interface
src/
  config.py                settings from .env
  services/ai_service.py   validation, ingestion, retrieval, prompting, error handling
  capabilities/rag.py      load_document, chunk_text, VectorStore
  models/model_client.py   Ollama chat (JSON output) + embeddings
  schemas/responses.py     Pydantic schemas (ModelAnswer, AnswerResponse, Source, ...)
data/sample/               sample course notes used for evaluation
evaluation/                test cases, evaluation script and results
tests/                     pytest unit tests (run without Ollama)
docs/                      architecture and decision log
```
> **Core Architectural Rule:** The user interface communicates only with
> the service layer (`src/services/ai_service.py`). The service layer
> coordinates document processing, retrieval and model calls. The interface
> never accesses the model client, vector store or Ollama directly.

## Model

- **Model used:** e.g., `llama3.2` (or specified local Ollama model)
- **Selection rationale:** Why was this specific model chosen for your project (e.g., lightweight, performance, context size)?

## Additional AI capability

- [x] RAG (Retrieval-Augmented Generation)
- [] Tools / External API integration
- [] Model Context Protocol (MCP)
- [] Agentic workflow (Model-selected actions based on observations)
- [] Memory / Persistent state
- [] Multimodal interaction (Text + Images)
- [] Other: ______________________

### Capability justification
The LLM doesn't know the student's course materials, and the materials are too long to fit into a single prompt. **RAG** solves this problem: it retrieves only the relevant parts of the uploaded files and gives them to the model as context. This:
- keeps answers grounded in the actual course content and reduces hallucinations,
- lets the app show **which file and page** an answer came from, so students can verify it,
- works with any course, because students just upload new materials and no retraining is needed.

## Setup

### 1. Create the Conda environment

```bash
conda env create -f environment.yml
```

### 2. Activate the environment

```bash
conda activate dev-ai-project
```

### 3. Configure environment variables

Copy `.env.example` to create your local `.env` configuration file:

On Linux / macOS:
```bash
cp .env.example .env
```

On Windows (Command Prompt / PowerShell):
```powershell
copy .env.example .env
```

Ensure `.env` contains valid values for `OLLAMA_BASE_URL`, `MODEL_NAME`and`EMBED_MODEL_NAME`:
```env
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=llama3.2
EMBED_MODEL_NAME=nomic-embed-text
```
Optional RAG settings (`CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, `MIN_SIMILARITY`) and guardrail limits (`MAX_QUESTION_CHARS`, `MAX_FILE_MB`) are listed in `.env.example`.

### 4. Start Ollama

Make sure Ollama is installed and running locally, then pull your configured model:

```bash
ollama run llama3.2
ollama pull nomic-embed-text
```

### 5. Run the application

Run the application from the root directory of the project:

```bash
python -m app.main
```

Then open your browser at `http://localhost:7860`, upload one or more files (for example `data/sample/ai_applications_notes.md`), click **Add to library**, and ask a question.

### 6. Run automated tests
The unit tests use a mock model client, so they run without Ollama:
```bash
pytest
```

## Evaluation

We will evaluate the application with representative test cases in [`evaluation/test_cases.json`](evaluation/test_cases.json), using sample course materials:

| Category | Planned cases | What will be checked |
|---|---|---|
| Successful | ~5 | Correct answer from the materials, with the right file and page |
| Difficult | ~3 | Paraphrased questions, questions needing several pages, a question in Finnish |
| Failure | ~4 | Out-of-scope question, prompt injection, empty input, too-long input |

**Planned metrics:** answer correctness, citation correctness (right file and page), correct refusal for questions the materials don't cover, and response time. Unit tests (`pytest`) will cover input validation, chunking, retrieval and error handling. Results will be summarized in [`evaluation/evaluation_results.md`](evaluation/evaluation_results.md).

## Known limitations

- Scanned PDFs without a text layer can't be read, because OCR isn't planned.
- A small local model may give weaker answers than large cloud models, and it can still make mistakes.
- Complex tables, formulas and diagrams in slides may not be understood correctly.
- Performance depends on the user's computer, and answers may be slow without a GPU.
- The similarity threshold (`MIN_SIMILARITY`) is a simple heuristic and may need tuning for other embedding models.
- One shared document library is used for everyone who opens the app; there are no separate user accounts.

## Future improvements

- Practice quiz generation from the materials (if not completed in the main scope).
- Memory: save quiz history and focus on the student's weak topics.
- Support for more file types (PowerPoint, Word).
- OCR for scanned documents.
- Flashcard export (for example to Anki).
- Multi-language support (Finnish and English).

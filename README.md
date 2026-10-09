# Finland Bureaucracy Helper
An AI assistant that answers international students questions about Finnish bureaucracy (residence permits, DVV registration, Kela, tax card) using official documents, and shows the sources.

**Disclaimer:** This application provides general guidance only and is **not legal advice**. Always confirm with the official authority (Migri, DVV, Kela, Vero).

## Team members

- Santosh Sigdel (santosh23000@student.hamk.fi, santosh.sigdel900@gmail.com)
- Puran karki (amk1002351@student.hamk.fi)
- Manoj Bhattarai (amk1006124@student.hamk.fi)
- Nabin Yari (amk1004480@student.hamk.fi)

### Intended users
International students, especially **non-EU students**, who are newly arrived or living in Finland and need to deal with Finnish authorities.
  
### Problem 
International students must complete many official processes, such as residence permits, address registration, Kela and tax cards. The information is spread across several government websites (Migri, DVV, Kela, Vero), International students must complete several official processes, often in a language they don't speak:

- Applying for and **extending a residence permit** (Migri)
- **Registering an address** and getting a **personal identity code** (DVV)
- Getting a **tax card** and understanding taxes when working (Vero)
- Understanding **Kela** benefits and eligibility
- Knowing **work-hour limits** for students

The information is **scattered across many official websites**, written in **long, formal language**, and often **depends on the student's situation** (EU or non-EU, permit type, length of stay). Students waste time, miss steps or rely on unreliable advice from social media groups.

## Main user need
"I want a quick, clear and **trustworthy** answer to my bureaucracy question that fits **my situation** and tells me **where the information comes from**.

### Why AI is appropriate
- Students can ask questions in their own words. AI understands the meaning, not just keywords.
- AI summarises long official text into a short, clear answer.
- With RAG, answers come from official documents with sources, so the model doesn't make up rules.

## Solution

StudyBuddy is a Gradio web app backed by a local LLM (Ollama). The student uploads course materials (PDF or text). The app splits the materials into chunks, embeds them and stores them in a local vector database.

Core task (main focus): The student asks a question in natural language. The app retrieves the most relevant parts of the materials, and the LLM answers using only that content, citing the file and page. If the answer isn't in the materials, the app says so instead of guessing.

Optional extra (only if the core works reliably): generate a short practice quiz on a chosen topic from the same retrieved content.

How it helps the user: students find answers faster, the answers match what was actually taught in the course (not general internet knowledge), students can verify every answer through the source reference, and their files stay private because everything runs locally.

## Main user workflow

1. Upload materials: The user uploads PDF or text files in the Gradio UI. The service layer extracts text, splits it into chunks, creates embeddings and stores them in the vector database.
2. User input: The user types a question about the course materials.
3. Processing and guardrails: src/services/ai_service.py validates the input (for example empty or too-long input, or no  uploaded files) and retrieves the most relevant chunks.
4. Model response: The model client sends a prompt containing the retrieved context to Ollama. The answer is returned through the service layer to the UI together with the source references.
5. Verify: The user can open the cited file and page to check the answer.

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

About 25 test questions covering:
- normal questions
- questions whose answer depends on the profile
- questions not covered by the documents (the app should say "I don't know")
- off-topic questions
- failure cases (Ollama not running, empty input)

## Known limitations

- Not legal advice. Rules may change after the documents were collected.
- English sources only.
- Covers common student topics only.

## Future improvements

- Practice quiz generation from the materials (if not completed in the main scope).
- Memory: save quiz history and focus on the student's weak topics.
- Support for more file types (PowerPoint, Word).
- OCR for scanned documents.
- Flashcard export (for example to Anki).
- Multi-language support (Finnish and English).

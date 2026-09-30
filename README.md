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

> **Core Architectural Rule:** The user interface must NEVER communicate directly with the model client or Ollama. All interactions must pass through the service layer (`ai_service.py`).

## Model

- **Model used:** e.g., `llama3.2` (or specified local Ollama model)
- **Selection rationale:** Why was this specific model chosen for your project (e.g., lightweight, performance, context size)?

## Additional AI capability

Select at least one additional capability to implement for your final project:

- [ ] RAG (Retrieval-Augmented Generation)
- [ ] Tools / External API integration
- [ ] Model Context Protocol (MCP)
- [ ] Agentic workflow (Model-selected actions based on observations)
- [ ] Memory / Persistent state
- [ ] Multimodal interaction (Text + Images)
- [ ] Other: ______________________

### Capability justification
Explain why the selected capability is useful and necessary for your application's user problem.

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

Ensure `.env` contains valid values for `OLLAMA_BASE_URL` and `MODEL_NAME`:
```env
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=llama3.2
```

### 4. Start Ollama

Make sure Ollama is installed and running locally, then pull your configured model:

```bash
ollama run llama3.2
```

### 5. Run the application

Run the application from the root directory of the project:

```bash
python -m app.main
```

Then open your browser at `http://localhost:7860`.

### 6. Run automated tests

```bash
pytest
```

## Evaluation

The evaluation uses the sample notes in [`data/sample/`](data/sample/) and the 12 cases in [`evaluation/test_cases.json`](evaluation/test_cases.json):

| Category | Cases | What is checked |
|---|---|---|
| Successful | 5 | Correct answer from the materials, with the right source |
| Difficult | 3 | Paraphrased question, multi-part question, Finnish question |
| Failure | 4 | Out-of-scope question, prompt injection, empty input, too-long input |

`evaluation/run_evaluation.py` runs every case through the real application, writes the actual answers into `test_cases.json`, and gives a first automatic pass/fail (expected success, "found in materials" flag, keywords). We then read every answer ourselves, correct the status where needed, and summarize the results in [`evaluation/evaluation_results.md`](evaluation/evaluation_results.md).

In addition, 25 automated unit tests (`pytest`) cover chunking, the vector store, input validation, invalid JSON with retry, fallback sources, and Ollama connection / missing-model errors.

**Results:** **

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

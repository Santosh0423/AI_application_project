# Project name

This is documentation for the **Development of AI Applications** course final group project.

## Team members

- Santosh Sigdel (santosh23000@student.hamk.fi, santosh.sigdel900@gmail.com)
-Puran karki (amk1002351@student.hamk.fi)
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

1. **User Input:** The user submits a prompt or query via the Gradio user interface.
2. **Processing & Guardrails:** The application service layer (`src/services/ai_service.py`) validates and formats the request.
3. **Model Response:** The model client calls Ollama locally and returns the response back through the service layer to the UI.

## Architecture

Below is the initial starter architecture. As your project evolves with additional capabilities, replace or extend this diagram in [`docs/architecture.md`](docs/architecture.md).

```text
User
  ↓
Gradio UI (app/ui.py)
  ↓
Application / AI Service (src/services/ai_service.py)
  ↓
Model Client (src/models/model_client.py)
  ↓
Ollama (Local LLM Server)
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

Describe your evaluation methodology and summarize key results. Starter test cases can be found in [`evaluation/test_cases.json`](evaluation/test_cases.json).

Refer to [`evaluation/README.md`](evaluation/README.md) for guidelines on defining success, edge cases, and failure scenarios.

## Known limitations

- Highlight known system limitations, unhandled edge cases, or boundaries of current capabilities.

## Future improvements

- List planned feature enhancements, architectural refactorings, or future capabilities.

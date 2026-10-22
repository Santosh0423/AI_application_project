# Evaluation Framework

We evaluate whether the Finland Bureaucracy Helper gives **correct, grounded, cited answers** and **refuses safely** when it cannot answer.

## Test cases

[`test_cases.json`](test_cases.json) contains **29 cases** in the template's three categories:

| Category | Cases | Types |
|---|---|---|
| **Successful cases** | 17 | Standard questions with known answers in the official pages (e.g. 30 h/week work limit, €800/month, 45 credits/year, 35 % tax at source) |
| **Difficult cases** | 4 | Profile-dependent answers (EU vs non-EU), and a short follow-up question that needs the previous question |
| **Failure / edge cases** | 8 | In-scope questions the documents don't cover, off-topic questions, prompt injection, empty and too-long input |

Each case has `input`, `expected_behavior`, `expected_status` and, for answerable questions, `expected_sources` (URL fragments) and `expected_keywords` (facts that must appear).

## Running the evaluation

Ollama must be running and the index built (`python scripts/ingest.py`). Then:

```bash
python evaluation/run_eval.py
```

The script asks every question through the same `AIService` the UI uses, then:
- fills in `actual_result`, `status` and `checks` in `test_cases.json`,
- writes the summary tables to [`evaluation_results.md`](evaluation_results.md).

## How a case is judged

| Status | Meaning |
|---|---|
| **pass** | Correct outcome (answered / refused / rejected). For answered questions, the expected source is cited **and** the key facts are present |
| **partial** | Answered, but the expected source wasn't cited or a key fact is missing |
| **fail** | Wrong outcome, e.g. it answered when it should have refused, or the other way round |

Automatic checks don't replace reading the answers. Review `actual_result` for each case and describe failures in `evaluation_results.md`.

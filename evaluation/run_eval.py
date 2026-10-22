"""Run the evaluation cases in test_cases.json and record the results.

Usage:  python evaluation/run_eval.py

- Fills in `actual_result`, `status` (pass / partial / fail) and `checks` for every
  case in evaluation/test_cases.json.
- Writes the summary to evaluation/evaluation_results.md.
"""

import json
import statistics
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.capabilities.memory import UserProfile  # noqa: E402
from src.capabilities.rag.retriever import Retriever  # noqa: E402
from src.capabilities.rag.store import IndexNotFoundError, VectorStore  # noqa: E402
from src.config import load_settings  # noqa: E402
from src.models.model_client import ModelClientError, OllamaModelClient  # noqa: E402
from src.services.ai_service import AIService  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
CASES_FILE = EVAL_DIR / "test_cases.json"
RESULTS_FILE = EVAL_DIR / "evaluation_results.md"
LONG_INPUT = "Please explain residence permits. " * 30
CATEGORY_NAMES = {
    "successful_case": "Successful Cases",
    "difficult_case": "Difficult Cases",
    "failure_case": "Failure / Edge Cases",
}


def keywords_ok(answer: str, groups: list[list[str]]) -> bool:
    """Every group must match; within a group any alternative is enough."""
    text = answer.lower()
    return all(any(alt.lower() in text for alt in group) for group in groups)


def judge(case: dict, checks: dict) -> str:
    if not checks["status_ok"]:
        return "fail"
    if case["expected_status"] != "answered":
        return "pass"
    other = [checks[k] for k in ("source_cited", "keywords_ok") if checks[k] is not None]
    return "pass" if all(other) else "partial"


def run() -> int:
    settings = load_settings()
    client = OllamaModelClient(settings.ollama_base_url, settings.model_name, settings.embed_model,
                               timeout=settings.request_timeout, temperature=settings.llm_temperature)
    try:
        missing = client.missing_models()
    except ModelClientError as exc:
        print(f"ERROR: {exc.user_message}")
        return 1
    if missing:
        print(f"ERROR: missing models: {missing}. Run `ollama pull <model>`.")
        return 1
    try:
        store = VectorStore.load(settings.index_dir)
    except IndexNotFoundError as exc:
        print(f"ERROR: {exc.user_message}")
        return 1

    retriever = Retriever(client, store, settings.top_k, settings.min_similarity)
    service = AIService(retriever, client, settings.max_question_chars, settings.history_turns)
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))

    for case in cases:
        question = LONG_INPUT if case["input"] == "LONG_INPUT" else case["input"]
        profile = UserProfile(**case.get("profile", {}))
        history = [tuple(h) for h in case.get("history", [])]

        # Raw similarity score (no threshold) helps tune MIN_SIMILARITY.
        top_score = None
        if question.strip() and len(question) <= settings.max_question_chars:
            scored = retriever.retrieve_all_scores(service._retrieval_query(question, history))
            top_score = round(scored[0].score, 3) if scored else None

        start = time.perf_counter()
        resp = service.answer(question, profile, history)
        seconds = round(time.perf_counter() - start, 2)

        expected_sources = case.get("expected_sources", [])
        retrieved_urls = [r.chunk.url for r in resp.retrieved]
        cited_urls = [s.url for s in resp.sources]
        checks = {
            "got_status": resp.status,
            "status_ok": resp.status == case["expected_status"],
            "retrieval_hit": any(e in u for e in expected_sources for u in retrieved_urls) if expected_sources else None,
            "source_cited": any(e in u for e in expected_sources for u in cited_urls) if expected_sources else None,
            "keywords_ok": keywords_ok(resp.answer, case["expected_keywords"]) if "expected_keywords" in case else None,
            "cited_correctly": resp.cited_correctly if resp.status == "answered" else None,
            "top_similarity": top_score,
            "seconds": seconds,
            "sources": cited_urls,
        }
        case["actual_result"] = resp.answer
        case["status"] = judge(case, checks)
        case["checks"] = checks
        print(f"[{case['status'].upper():7}] {case['id']:4} {resp.status:13} {seconds:6.1f}s  "
              f"sim={top_score}  {question[:60]}", flush=True)

    CASES_FILE.write_text(json.dumps(cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    RESULTS_FILE.write_text(to_markdown(settings, len(store), cases), encoding="utf-8")
    print(f"\nUpdated {CASES_FILE.name} and wrote {RESULTS_FILE.name}")
    return 0


def rate(cases: list[dict], key: str) -> str:
    values = [c["checks"][key] for c in cases if c["checks"][key] is not None]
    if not values:
        return "–"
    return f"{sum(values)}/{len(values)} ({100 * sum(values) / len(values):.0f}%)"


def to_markdown(settings, n_chunks: int, cases: list[dict]) -> str:
    passed = sum(c["status"] == "pass" for c in cases)
    partial = sum(c["status"] == "partial" for c in cases)
    failed = sum(c["status"] == "fail" for c in cases)
    answered = [c for c in cases if c["expected_status"] == "answered"]
    refusals = [c for c in cases if c["expected_status"] == "not_found"]
    invalid = [c for c in cases if c["expected_status"] == "invalid_input"]
    times = [c["checks"]["seconds"] for c in cases if c["checks"]["got_status"] in ("answered", "not_found")]

    lines = [
        "# Evaluation Results Summary",
        "",
        "Generated by `python evaluation/run_eval.py`. Full answers are in `test_cases.json` (`actual_result`).",
        "",
        "## Summary Overview",
        "",
        f"- **Date of Evaluation:** {date.today().isoformat()}",
        f"- **Model Evaluated:** `{settings.model_name}` (embeddings: `{settings.embed_model}`)",
        f"- **Settings:** top_k={settings.top_k}, min_similarity={settings.min_similarity}, "
        f"chunk_size={settings.chunk_size}, {n_chunks} chunks in index",
        f"- **Total Test Cases Executed:** {len(cases)}",
        f"- **Passed:** {passed}",
        f"- **Partial:** {partial}",
        f"- **Failed:** {failed}",
        f"- **Pass Rate:** {100 * passed / len(cases):.0f}%",
        "",
        "## Performance by Category",
        "",
        "| Category | Total Cases | Passed | Partial | Failed | Pass Rate |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for key, name in CATEGORY_NAMES.items():
        group = [c for c in cases if c["category"] == key]
        if not group:
            continue
        p = sum(c["status"] == "pass" for c in group)
        pa = sum(c["status"] == "partial" for c in group)
        f = sum(c["status"] == "fail" for c in group)
        lines.append(f"| {name} | {len(group)} | {p} | {pa} | {f} | {100 * p / len(group):.0f}% |")

    lines += [
        "",
        "## RAG Quality Metrics",
        "",
        "| Metric | Result |",
        "| :--- | :---: |",
        f"| Answerable questions answered | {rate(answered, 'status_ok')} |",
        f"| Retrieval hit (expected source in top-k) | {rate(answered, 'retrieval_hit')} |",
        f"| Expected source cited in answer | {rate(answered, 'source_cited')} |",
        f"| Key facts present in answer | {rate(answered, 'keywords_ok')} |",
        f"| Answers with valid [n] citations | {rate(answered, 'cited_correctly')} |",
        f"| Correct refusals (unanswerable + off-topic) | {rate(refusals, 'status_ok')} |",
        f"| Invalid input rejected | {rate(invalid, 'status_ok')} |",
        (f"| Avg / max response time | {statistics.mean(times):.1f}s / {max(times):.1f}s |"
         if times else "| Response time | – |"),
        "",
        "## Per Case",
        "",
        "| ID | Type | Input | Expected | Got | Retrieval | Cited | Facts | Top sim | Time | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    mark = {True: "✅", False: "❌", None: "–"}
    for c in cases:
        k = c["checks"]
        text = c["input"] if len(c["input"]) < 70 else c["input"][:67] + "..."
        lines.append(
            f"| {c['id']} | {c['type']} | {text.replace('|', '/')} | {c['expected_status']} | {k['got_status']} | "
            f"{mark[k['retrieval_hit']]} | {mark[k['source_cited']]} | {mark[k['keywords_ok']]} | "
            f"{k['top_similarity'] if k['top_similarity'] is not None else '–'} | {k['seconds']}s | {c['status']} |"
        )

    lines += [
        "",
        "## Key Findings & Failure Analysis",
        "",
        "### What worked well",
        "- _Fill in after reviewing the results._",
        "",
        "### Observed failure modes",
        "- _Describe each partial/failed case and why it happened._",
        "",
        "## Action Items & Improvements",
        "- [ ] _Planned fix or enhancement based on the findings._",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(run())

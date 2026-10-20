from src.models.model_client import ModelTimeoutError, OllamaConnectionError
from src.capabilities.rag.documents import Chunk
from src.capabilities.rag.store import SearchResult
from src.services.ai_service import NOT_FOUND_MESSAGE, AIService
from src.capabilities.memory import UserProfile


def result(i: int, url: str | None = None) -> SearchResult:
    chunk = Chunk(id=str(i), text=f"Fact number {i}.", title=f"Page {i}", url=url or f"https://migri.fi/{i}",
                  authority="Migri", retrieved="2026-10-17")
    return SearchResult(chunk, 0.8)


class FakeRetriever:
    def __init__(self, results=None, error=None):
        self.results = results if results is not None else [result(1), result(2)]
        self.error = error
        self.queries = []

    def retrieve(self, query):
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.results


class FakeModel:
    def __init__(self, reply="Students can work 30 hours per week [1].", error=None):
        self.reply = reply
        self.error = error
        self.messages = None

    def chat(self, messages):
        self.messages = messages
        if self.error:
            raise self.error
        return self.reply


def test_answer_with_valid_citation():
    model = FakeModel("You can work 30 hours per week [2].")
    resp = AIService(FakeRetriever(), model).answer("Can I work?")
    assert resp.status == "answered"
    assert resp.cited_correctly
    assert [s.title for s in resp.sources] == ["Page 2"]
    assert "[1]" in resp.answer  # renumbered to match the Sources list
    assert "Sources" in resp.to_markdown()


def test_empty_question_is_rejected_without_calling_model():
    model = FakeModel()
    resp = AIService(FakeRetriever(), model).answer("   ")
    assert resp.status == "invalid_input"
    assert model.messages is None


def test_too_long_question_is_rejected():
    resp = AIService(FakeRetriever(), FakeModel(), max_question_chars=20).answer("x" * 21)
    assert resp.status == "invalid_input"


def test_no_relevant_documents_returns_not_found_without_model_call():
    model = FakeModel()
    resp = AIService(FakeRetriever(results=[]), model).answer("Write me a poem")
    assert resp.status == "not_found"
    assert resp.answer == NOT_FOUND_MESSAGE
    assert model.messages is None


def test_model_not_found_token_becomes_refusal():
    resp = AIService(FakeRetriever(), FakeModel("NOT_FOUND")).answer("Bus ticket price?")
    assert resp.status == "not_found"


def test_invalid_citation_numbers_are_removed():
    resp = AIService(FakeRetriever(), FakeModel("Fact [1] and invented [7].")).answer("q")
    assert "[7]" not in resp.answer
    assert resp.cited_correctly


def test_answer_without_citations_gets_note_and_all_sources():
    resp = AIService(FakeRetriever(), FakeModel("Some answer without citations.")).answer("q")
    assert resp.status == "answered"
    assert not resp.cited_correctly
    assert len(resp.sources) == 2
    assert "did not cite" in resp.answer


def test_duplicate_pages_are_merged_in_sources():
    same = "https://migri.fi/same"
    retriever = FakeRetriever([result(1, same), result(2, same)])
    resp = AIService(retriever, FakeModel("A [1]. B [2].")).answer("q")
    assert len(resp.sources) == 1
    assert "[2]" not in resp.answer


def test_model_unavailable_gives_friendly_error():
    resp = AIService(FakeRetriever(), FakeModel(error=OllamaConnectionError("down"))).answer("q")
    assert resp.status == "error"
    assert "Ollama" in resp.answer


def test_model_timeout_gives_friendly_error():
    resp = AIService(FakeRetriever(), FakeModel(error=ModelTimeoutError("slow"))).answer("q")
    assert resp.status == "error"
    assert "too long" in resp.answer


def test_embedding_failure_during_retrieval_is_handled():
    resp = AIService(FakeRetriever(error=OllamaConnectionError("down")), FakeModel()).answer("q")
    assert resp.status == "error"


def test_missing_index_is_reported():
    resp = AIService(None, FakeModel()).answer("q")
    assert resp.status == "error"
    assert "ingest" in resp.answer


def test_profile_and_context_are_in_prompt():
    model = FakeModel()
    profile = UserProfile(citizenship="Non-EU citizen", student_type="Degree student")
    AIService(FakeRetriever(), model).answer("Can I work?", profile)
    prompt = model.messages[-1]["content"]
    assert "Non-EU citizen" in prompt
    assert "[1]" in prompt and "Fact number 1." in prompt


def test_short_follow_up_uses_previous_question_for_retrieval():
    retriever = FakeRetriever()
    history = [("Can I work while studying?", "Yes, 30 hours per week [1].")]
    AIService(retriever, FakeModel()).answer("What about holidays?", history=history)
    assert "Can I work while studying?" in retriever.queries[0]

from agent.agent_book import UNCOVERED, run_example
from knowledge.ingest import run_ingest


def test_example_returns_day_to_day_scenario():
    run_ingest()
    result = run_example(topic="data warehouse")
    assert result["covered"] is True
    assert result["steps"] == ["expand", "retrieve", "example"]
    assert "dia a dia" in result["scenario"].lower()
    assert result["citations"]
    assert all("page" in item for item in result["citations"])


def test_example_uncovered_topic():
    run_ingest()
    result = run_example(topic="How do quantum qubits teleport beer recipes?")
    assert result["covered"] is False
    assert result["scenario"] == UNCOVERED


def test_example_uses_llm_when_provider_is_azure(monkeypatch):
    class StubLlm:
        def complete(self, *, system: str, user: str) -> str:
            if "Excerpts:" not in user:
                return user.replace("User query:", "").strip()
            assert "Topic:" in user
            return (
                "Contexto: um varejo usa warehouse para decisao.\n"
                "Situação do dia a dia: o time publica fatos no warehouse (p.2)."
            )

    monkeypatch.setenv("AGENT_BOOK_LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setattr("agent.agent_book.build_llm", lambda provider, cfg: StubLlm())
    run_ingest()
    result = run_example(topic="data warehouse")
    assert "varejo" in result["scenario"]
    assert result["covered"] is True

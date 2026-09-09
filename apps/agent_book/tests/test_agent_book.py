from agent.agent_book import UNCOVERED, run_ask
from connectors.llm import resolve_llm_provider
from knowledge.ingest import run_ingest


def test_ask_returns_citations_from_book():
    run_ingest()
    result = run_ask(question="O que e o ciclo de vida da engenharia de dados?")
    assert result["covered"] is True
    assert result["citations"]
    assert all("page" in item for item in result["citations"])
    assert "p." in result["answer"]


def test_ask_uncovered_topic():
    run_ingest()
    result = run_ask(question="How do quantum qubits teleport beer recipes?")
    assert result["covered"] is False
    assert result["answer"] == UNCOVERED
    assert result["citations"] == []


def test_resolve_llm_provider_prefers_env(monkeypatch):
    monkeypatch.setenv("AGENT_BOOK_LLM_PROVIDER", "azure_openai")
    assert resolve_llm_provider({"llm_provider": "echo"}) == "azure_openai"
    monkeypatch.delenv("AGENT_BOOK_LLM_PROVIDER")
    assert resolve_llm_provider({"llm_provider": "echo"}) == "echo"


def test_ask_uses_llm_when_provider_is_azure(monkeypatch):
    class StubLlm:
        def complete(self, *, system: str, user: str) -> str:
            if "Excerpts:" not in user:
                return user.replace("User query:", "").strip()
            assert "Original question:" in user
            assert "Excerpts:" in user
            return "O ciclo cobre geracao, armazenamento e ingestao (p.1)."

    monkeypatch.setenv("AGENT_BOOK_LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setattr("agent.agent_book.build_llm", lambda provider, cfg: StubLlm())
    run_ingest()
    result = run_ask(question="O que e o ciclo de vida da engenharia de dados?")
    assert result["covered"] is True
    assert result["answer"].startswith("O ciclo cobre")
    assert "Pergunta:" not in result["answer"]


def test_expand_query_echo_keeps_original():
    from agent.agent_book import AgentBook

    agent = AgentBook()
    assert agent.expand_query("paralelismo") == "paralelismo"


def test_expand_query_uses_llm_synonyms(monkeypatch):
    from agent.agent_book import AgentBook

    class StubLlm:
        def complete(self, *, system: str, user: str) -> str:
            del system
            assert "User query:" in user
            return "paralelismo processamento paralelo embarrassingly parallel Spark MPP"

    monkeypatch.setenv("AGENT_BOOK_LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setattr("agent.agent_book.build_llm", lambda provider, cfg: StubLlm())
    agent = AgentBook()
    expanded = agent.expand_query("o que e paralelismo")
    assert "Spark" in expanded
    assert "MPP" in expanded


def test_ask_runner_bootstraps(monkeypatch):
    import sys

    from workflows.runs import agent as runner

    monkeypatch.setattr(
        sys,
        "argv",
        ["agent.py", "ask", "--question", "data warehouse"],
    )
    runner.main()

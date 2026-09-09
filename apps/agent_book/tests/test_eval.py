import os

import pytest

from agent.agent_book import AgentBook, invoke_agent_book
from dataplatform.lake import Layer
from evals.runner import azure_ready, run_golden
from knowledge.ingest import run_ingest
from usecases.results import AskResult


def test_golden_eval_fixture_passes():
    report = run_golden()
    failed = [row for row in report if not row["ok"]]
    assert not failed, failed


@pytest.mark.azure
@pytest.mark.skipif(
    os.getenv("AGENT_BOOK_EVAL_AZURE") != "1" or not azure_ready(),
    reason="opt-in Azure eval: python apps/agent_book/evals/run_azure.py",
)
def test_golden_eval_azure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_BOOK_LLM_PROVIDER", "azure_openai")
    report = run_golden(require_llm=True)
    failed = [row for row in report if not row["ok"]]
    assert not failed, failed


def test_require_llm_rejects_echo_answers():
    report = run_golden(require_llm=True)
    lifecycle = next(row for row in report if row["id"] == "lifecycle")
    assert lifecycle["ok"] is False
    assert any("echo template" in err for err in lifecycle["errors"])


def test_require_llm_passes_with_stub_model(monkeypatch: pytest.MonkeyPatch):
    class StubLlm:
        def complete(self, *, system: str, user: str) -> str:
            del system
            if "Excerpts:" not in user:
                return user.replace("User query:", "").strip()
            head = user.split("Excerpts:")[0].lower()
            if "warehouse" in head:
                return "O data warehouse e um padrao para analise (p.2)."
            if "medallion" in head:
                return "Arquitetura medallion usa bronze, silver e gold (p.3)."
            return "O ciclo de vida cobre geracao e ingestao (p.1)."

        def reset_usage(self) -> None:
            return None

    monkeypatch.setenv("AGENT_BOOK_LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setattr("agent.agent_book.build_llm", lambda provider, cfg: StubLlm())
    report = run_golden(require_llm=True)
    failed = [row for row in report if not row["ok"]]
    assert not failed, failed


def test_ask_returns_typed_result():
    run_ingest()
    agent = AgentBook()
    hits = agent.retrieve("data warehouse")
    payload = agent.book.ask("data warehouse", hits)
    assert isinstance(payload, AskResult)
    assert payload.covered is True
    assert payload.citations[0].page == 2


def test_retrieve_without_ingest_is_uncovered():
    result = invoke_agent_book(task="ask", query="ciclo de vida")
    assert result["covered"] is False
    assert result["steps"] == ["expand", "retrieve", "uncovered"]


def test_graph_is_compiled_once():
    agent = AgentBook()
    assert agent.graph() is agent.graph()


def test_trace_records_chunks_and_prompt():
    run_ingest()
    agent = AgentBook()
    result = agent.invoke(
        task="ask", query="O que e o ciclo de vida da engenharia de dados?"
    )
    trace = result["trace"]
    assert result["prompt_id"] == "ask.v1"
    assert result["prompt_sha"]
    assert trace["chunk_ids"]
    assert trace["elapsed_ms"] >= 0
    assert trace["steps"] == ["expand", "retrieve", "ask"]
    stored = agent.io.read_json(agent.paths.table_path(Layer.GOLD, "agent", "trace"))
    assert stored[0]["prompt_id"] == "ask.v1"

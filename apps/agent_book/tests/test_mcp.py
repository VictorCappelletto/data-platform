import asyncio
import importlib.util

import pytest

from agent.agent_book import UNCOVERED
from knowledge.ingest import run_ingest
from mcp_server.tools import ask_book, chat_book, example_book, feedback_book, note_book, quote_book


def test_mcp_ask_book_returns_citations():
    run_ingest()
    result = ask_book("O que e o ciclo de vida da engenharia de dados?")
    assert result["covered"] is True
    assert result["citations"]
    assert result["steps"] == ["expand", "retrieve", "ask"]
    assert result["offer_example"] is True


def test_mcp_note_book_persists_gold():
    run_ingest()
    result = note_book("data warehouse")
    assert result["covered"] is True
    assert result["note_key"].startswith("NOTE-")
    assert result["claim"]
    assert result["steps"] == ["expand", "retrieve", "note"]


def test_mcp_example_book_returns_scenario():
    run_ingest()
    result = example_book("data warehouse")
    assert result["covered"] is True
    assert result["scenario"]
    assert result["steps"] == ["expand", "retrieve", "example"]


def test_mcp_quote_book_returns_passages():
    run_ingest()
    result = quote_book("data warehouse")
    assert result["covered"] is True
    assert result["passages"]
    assert result["steps"] == ["expand", "retrieve", "quote"]


def test_mcp_chat_routes_free_form():
    run_ingest()
    result = chat_book("o que e data warehouse?")
    assert result["routed"] == "ask"
    assert result["covered"] is True


def test_mcp_feedback_records_positive():
    run_ingest()
    ask_book("data warehouse")
    result = feedback_book(comment="gostei, objetiva", positive=True)
    assert result["recorded"] is True
    assert result["profile"]["positive_count"] >= 1


def test_mcp_ask_uncovered():
    run_ingest()
    result = ask_book("How do quantum qubits teleport beer recipes?")
    assert result["covered"] is False
    assert result["answer"] == UNCOVERED


@pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="mcp extra not installed")
def test_mcp_server_registers_tools():
    from mcp_server.server import build_server

    tools = asyncio.run(build_server().list_tools())
    names = {tool.name for tool in tools}
    assert names == {
        "agent_book_ask",
        "agent_book_note",
        "agent_book_example",
        "agent_book_quote",
        "agent_book_chat",
        "agent_book_feedback",
    }

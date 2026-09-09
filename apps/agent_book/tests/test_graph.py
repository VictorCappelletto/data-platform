from agent.agent_book import AgentBook, build_agent_book_graph, invoke_agent_book
from knowledge.ingest import run_ingest


def test_graph_ask_steps_retrieve_then_ask():
    run_ingest()
    result = invoke_agent_book(task="ask", query="O que e o ciclo de vida da engenharia de dados?")
    assert result["steps"] == ["expand", "retrieve", "ask"]
    assert result["covered"] is True
    assert result["citations"]
    assert result["offer_example"] is True


def test_graph_note_steps_retrieve_then_note():
    run_ingest()
    result = invoke_agent_book(task="note", query="data warehouse")
    assert result["steps"] == ["expand", "retrieve", "note"]
    assert result["covered"] is True
    assert result["note_key"].startswith("NOTE-")


def test_graph_uncovered_stops_after_retrieve():
    run_ingest()
    result = invoke_agent_book(task="ask", query="How do quantum qubits teleport beer recipes?")
    assert result["steps"] == ["expand", "retrieve", "uncovered"]
    assert result["covered"] is False
    assert result["citations"] == []


def test_graph_example_steps():
    run_ingest()
    result = invoke_agent_book(task="example", query="data warehouse")
    assert result["steps"] == ["expand", "retrieve", "example"]
    assert result["covered"] is True
    assert result["scenario"]


def test_graph_compiles_expected_nodes():
    compiled = build_agent_book_graph(AgentBook())
    nodes = set(compiled.get_graph().nodes)
    assert {
        "route",
        "expand",
        "retrieve",
        "ask",
        "note",
        "example",
        "quote",
        "feedback",
        "uncovered",
    }.issubset(nodes)

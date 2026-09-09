from agent.agent_book import run_ask, run_chat, run_feedback, run_quote
from agent.router import bind_followup_query, is_followup, parse_route_payload, route_message
from connectors.llm import EchoLlm
from knowledge.ingest import run_ingest


class _RouteLlm:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def complete(self, *, system: str, user: str) -> str:
        assert "Tools:" in system
        assert "User message:" in user
        return self.payload


def test_echo_router_does_not_guess_the_tool():
    decision = route_message(EchoLlm(), "salva uma nota sobre data warehouse")
    assert decision.tool == "ask"
    assert "data warehouse" in decision.query.lower()


def test_llm_router_picks_note_from_intent():
    llm = _RouteLlm(
        '{"tool": "note", "query": "data warehouse", "feedback_positive": false}'
    )
    decision = route_message(llm, "pode guardar isso do warehouse pra eu estudar depois")
    assert decision.tool == "note"
    assert decision.query == "data warehouse"


def test_llm_router_picks_example_from_intent():
    llm = _RouteLlm(
        '{"tool": "example", "query": "pipeline", "feedback_positive": false}'
    )
    decision = route_message(llm, "tipo no trabalho, como isso aparece?")
    assert decision.tool == "example"
    assert decision.query == "pipeline"


def test_llm_router_picks_quote_from_intent():
    llm = _RouteLlm(
        '{"tool": "quote", "query": "ciclo de vida", "feedback_positive": false}'
    )
    decision = route_message(llm, "quero o texto do livro, nao o resumo")
    assert decision.tool == "quote"


def test_llm_router_picks_feedback_from_intent():
    llm = _RouteLlm('{"tool": "feedback", "query": "objetiva", "feedback_positive": true}')
    decision = route_message(llm, "ficou claro, continua nesse ritmo")
    assert decision.tool == "feedback"
    assert decision.feedback_positive is True


def test_llm_router_praise_plus_question_stays_ask():
    llm = _RouteLlm(
        '{"tool": "ask", "query": "ciclo de vida", "feedback_positive": true}'
    )
    decision = route_message(llm, "gostei, o que e o ciclo de vida?")
    assert decision.tool == "ask"
    assert decision.feedback_positive is True


def test_llm_router_uses_previous_topic():
    llm = _RouteLlm(
        '{"tool": "ask", "query": "data warehouse — nao entendi", "feedback_positive": false}'
    )
    decision = route_message(llm, "nao entendi", last_query="data warehouse")
    assert "data warehouse" in decision.query.lower()


def test_parse_route_payload_json():
    parsed = parse_route_payload(
        '{"tool": "quote", "query": "MPP", "feedback_positive": false}'
    )
    assert parsed is not None
    assert parsed.tool == "quote"
    assert parsed.query == "MPP"


def test_chat_routes_to_ask():
    run_ingest()
    result = run_chat(message="o que e o ciclo de vida da engenharia de dados?")
    assert result["routed"] == "ask"
    assert result["steps"][0] == "route"
    assert result["covered"] is True


def test_chat_routes_to_note(monkeypatch):
    class StubLlm:
        def complete(self, *, system: str, user: str) -> str:
            if "User message:" in user:
                return (
                    '{"tool": "note", "query": "data warehouse",'
                    ' "feedback_positive": false}'
                )
            return (
                '{"claim": "O data warehouse e a base analitica.",'
                ' "evidence": "- p.2 warehouse."}'
            )

    monkeypatch.setenv("AGENT_BOOK_LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setattr("agent.agent_book.build_llm", lambda provider, cfg: StubLlm())
    run_ingest()
    result = run_chat(message="guarda isso do warehouse pra estudar")
    assert result["routed"] == "note"
    assert result["note_key"].startswith("NOTE-")


def test_quote_returns_passages():
    run_ingest()
    result = run_quote(query="data warehouse")
    assert result["covered"] is True
    assert result["steps"] == ["expand", "retrieve", "quote"]
    assert result["passages"]
    assert all("text" in item and "page" in item for item in result["passages"])


def test_feedback_updates_profile():
    run_ingest()
    run_quote(query="data warehouse")
    result = run_feedback(comment="gostei, bem objetiva e com pagina")
    assert result["recorded"] is True
    assert result["profile"]["positive_count"] >= 1
    assert result["steps"] == ["feedback"]


def test_negative_feedback_is_ignored():
    result = run_feedback(comment="nao gostei", positive=False)
    assert result["recorded"] is False
    assert result["reason"] == "only_positive"


def test_is_followup_vague_and_relative():
    prior = "ciclo de vida da engenharia de dados"
    assert is_followup("nao entendi", prior) is True
    assert is_followup("e no Spark?", prior) is True
    assert is_followup("o que e data warehouse?", prior) is False


def test_bind_followup_prefixes_last_topic():
    bound, used = bind_followup_query("explica melhor", "data warehouse")
    assert used is True
    assert bound.startswith("data warehouse")
    assert "explica melhor" in bound
    bound, used = bind_followup_query("o que e medallion?", "data warehouse")
    assert used is False
    assert bound == "o que e medallion?"


def test_chat_followup_uses_last_topic():
    run_ingest()
    first = run_chat(message="o que e data warehouse?")
    assert first["followup"] is False
    assert first["covered"] is True
    second = run_chat(message="nao entendi")
    assert second["followup"] is True
    assert second["covered"] is True
    assert "data warehouse" in second["search_query"].lower()


def test_ask_followup_after_previous_turn():
    run_ingest()
    run_ask(question="data warehouse")
    result = run_ask(question="explica melhor")
    assert result["followup"] is True
    assert result["covered"] is True
    assert "data warehouse" in (result.get("question") or result["search_query"]).lower()

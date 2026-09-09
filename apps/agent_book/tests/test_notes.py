from agent.agent_book import UNCOVERED, run_note
from knowledge.ingest import run_ingest
from usecases.admin import parse_note_payload


def test_note_persists_structured_interpretation():
    run_ingest()
    result = run_note(topic="data warehouse")
    assert result["covered"] is True
    assert result["note_key"].startswith("NOTE-")
    assert result["pages"]
    assert result["claim"]
    assert "data warehouse" in result["claim"].lower()
    assert result["evidence"]
    assert result["uri"]


def test_note_uncovered_topic():
    run_ingest()
    result = run_note(topic="How do quantum qubits teleport beer recipes?")
    assert result["covered"] is False
    assert result["answer"] == UNCOVERED


def test_note_uses_llm_when_provider_is_azure(monkeypatch):
    class StubLlm:
        def complete(self, *, system: str, user: str) -> str:
            if "Excerpts:" not in user:
                return user.replace("User query:", "").strip()
            assert "Topic:" in user
            assert "Excerpts:" in user
            return (
                '{"claim": "O data warehouse e a base analitica da disciplina.",'
                ' "evidence": "- p.2 Bill Inmon descreve o warehouse como base."}'
            )

    monkeypatch.setenv("AGENT_BOOK_LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setattr("agent.agent_book.build_llm", lambda provider, cfg: StubLlm())
    run_ingest()
    result = run_note(topic="data warehouse")
    assert result["claim"] == "O data warehouse e a base analitica da disciplina."
    assert "p.2" in result["evidence"]


def test_parse_note_payload_accepts_fenced_json():
    parsed = parse_note_payload(
        '```json\n{"claim": "tese", "evidence": ["p.1 geracao", "p.2 warehouse"]}\n```'
    )
    assert parsed == {"claim": "tese", "evidence": "p.1 geracao\np.2 warehouse"}
    assert parse_note_payload('{"Claim": "Tese", "Evidence": "p.1"}') == {
        "claim": "Tese",
        "evidence": "p.1",
    }


def test_parse_note_payload_rejects_empty_claim():
    assert parse_note_payload('{"claim": "", "evidence": "x"}') is None
    assert parse_note_payload("not json") is None

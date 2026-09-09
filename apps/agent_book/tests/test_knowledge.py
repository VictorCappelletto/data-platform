import pytest

from knowledge.chunking import chunk_pages, split_pages
from knowledge.ingest import run_ingest
from knowledge.retrieve import KnowledgeRetriever


def test_split_pages_uses_form_feed():
    text = "pagina um sobre ingestao\n\nparagrafo.\n\x0cpagina dois sobre warehouse\n"
    pages = split_pages(text)
    assert len(pages) == 2
    assert pages[0][0] == 1
    assert "ingestao" in pages[0][1]
    assert pages[1][0] == 2


def test_chunk_pages_do_not_cross_page_boundary():
    pages = [
        (
            1,
            "A " * 40 + "ciclo de vida da engenharia de dados.\n\nOutro paragrafo na mesma pagina.",
        ),
        (2, "B " * 40 + "data warehouse e analise."),
    ]
    chunks = chunk_pages(
        pages,
        source_id="fx",
        source_path="book.txt",
        max_chars=200,
        overlap=40,
        min_chars=20,
    )
    assert chunks
    pages_used = {row["page"] for row in chunks}
    assert pages_used == {1, 2}
    for row in chunks:
        assert "ciclo" in row["text"] or "warehouse" in row["text"] or "paragrafo" in row["text"]
        if "warehouse" in row["text"] and "ciclo" not in row["text"]:
            assert row["page"] == 2


def test_ingest_and_retrieve_from_fixture():
    result = run_ingest()
    assert result["chunks"] > 0
    assert result["indexed"] == 0
    assert result["search_provider"] == "local"
    hits = KnowledgeRetriever().search("ciclo de vida engenharia de dados", top_k=4)
    assert hits
    assert any(hit.page >= 1 for hit in hits)
    blob = " ".join(hit.text.lower() for hit in hits)
    assert "ciclo" in blob or "engenharia" in blob


def test_missing_book_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_BOOK_BOOK_PATH", str(tmp_path / "missing.txt"))
    with pytest.raises(FileNotFoundError, match="Book not found"):
        run_ingest()

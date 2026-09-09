"""Set default app context for Agent Book tests. Book path is a tiny fixture."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ID = "agent_book"
APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]

FIXTURE_TEXT = """\
Capitulo 1
O ciclo de vida da engenharia de dados cobre geracao, armazenamento,
ingestao, transformacao e servico de dados.

\x0cCapitulo 2
O data warehouse e um padrao para analise. Bill Inmon descreve o warehouse
como a base da disciplina. Engenharia de dados nao e so uma ferramenta.

\x0cCapitulo 3
Arquitetura medallion usa camadas bronze, silver e gold. Este fixture nao
substitui o livro; so testa o pipeline de chunks.
"""

for path in (REPO_ROOT, APP_ROOT):
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mcp_server.tools import reset  # noqa: E402


@pytest.fixture(autouse=True)
def _app_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    book = tmp_path / "book.txt"
    book.write_text(FIXTURE_TEXT, encoding="utf-8")
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(REPO_ROOT))
    monkeypatch.setenv("DATA_PLATFORM_APP", APP_ID)
    monkeypatch.setenv("PLATFORM_ENV", "local")
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("AGENT_BOOK_BOOK_PATH", str(book))
    monkeypatch.delenv("AGENT_BOOK_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("AGENT_BOOK_SEARCH_PROVIDER", raising=False)
    reset()

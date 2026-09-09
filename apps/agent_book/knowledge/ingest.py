"""Ingest the book TXT into the Agent Book knowledge lake."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from connectors.search import build_search, resolve_search_provider
from dataplatform.lake import Layer
from dataplatform.process_base import ProjectProcessBase
from knowledge.chunking import chunk_pages, split_pages
from knowledge.retrieve import KnowledgeRetriever


class KnowledgeIngest(ProjectProcessBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("knowledge", "book", environment)

    @property
    def domain(self) -> str:
        return self.product_config["domain"]

    @property
    def table(self) -> str:
        return self.product_config["table"]

    def layer_path(self, layer: Layer | str) -> str:
        return self.paths.table_path(layer, self.domain, self.table)

    def resolve_book_path(self) -> Path:
        env_path = os.getenv("AGENT_BOOK_BOOK_PATH")
        if env_path:
            return Path(env_path)
        rel = str(self.product_config["path"])
        if Path(rel).is_absolute():
            return Path(rel)
        return self.loader.resolve_app_path(rel)

    def ingest(self) -> tuple[list[dict[str, Any]], str, int]:
        path = self.resolve_book_path()
        if not path.is_file():
            raise FileNotFoundError(
                f"Book not found: {path}. Copy the TXT into apps/agent_book/seeds/ "
                "or set AGENT_BOOK_BOOK_PATH."
            )
        text = path.read_text(encoding="utf-8", errors="replace")
        chunk_cfg = self.product_config.get("chunk", {})
        rows = chunk_pages(
            split_pages(text),
            source_id=str(self.product_config.get("source_id", "book")),
            source_path=path.name,
            max_chars=int(chunk_cfg.get("max_chars", 1200)),
            overlap=int(chunk_cfg.get("overlap", 180)),
            min_chars=int(chunk_cfg.get("min_chars", 80)),
        )
        dest = self.layer_path(Layer.BRONZE)
        written = self.io.write_json(dest, rows)
        self.logger.info("knowledge bronze: %s (%s chunks)", written, len(rows))
        indexed = self._index_vectors(rows)
        return rows, written, indexed

    def _index_vectors(self, rows: list[dict[str, Any]]) -> int:
        provider = resolve_search_provider(self.product_config)
        search = build_search(
            provider,
            retriever=KnowledgeRetriever(self.platform.environment),
            cfg=self.product_config,
        )
        search.ensure_index()
        indexed = search.upsert(rows)
        if indexed:
            self.logger.info("vector index upserted %s chunks (%s)", indexed, provider)
        return indexed


def run_ingest(environment: str | None = None) -> dict[str, Any]:
    ingest = KnowledgeIngest(environment)
    rows, path, indexed = ingest.ingest()
    return {
        "chunks": len(rows),
        "path": path,
        "search_provider": resolve_search_provider(ingest.product_config),
        "indexed": indexed,
    }

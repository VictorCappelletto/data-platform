"""Local keyword retrieve over bronze knowledge chunks."""

from __future__ import annotations

from dataplatform.lake import Layer
from dataplatform.process_base import ProjectProcessBase
from entities.issue import KnowledgeChunk


class KnowledgeRetriever(ProjectProcessBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("knowledge", "book", environment)

    def load_chunks(self) -> list[KnowledgeChunk]:
        path = self.paths.table_path(
            Layer.BRONZE, self.product_config["domain"], self.product_config["table"]
        )
        try:
            rows = self.io.read_json(path)
        except FileNotFoundError:
            return []
        return [
            KnowledgeChunk(
                id=str(row["id"]),
                source_id=str(row["source_id"]),
                source_path=str(row["source_path"]),
                title=str(row.get("title", "")),
                text=str(row.get("text", "")),
                page=int(row.get("page") or 0),
            )
            for row in rows
        ]

    def search(self, query: str, top_k: int = 4) -> list[KnowledgeChunk]:
        scored = sorted(
            ((_score(query, chunk), chunk) for chunk in self.load_chunks()),
            key=lambda item: item[0],
            reverse=True,
        )
        return [chunk for score, chunk in scored if score > 0][:top_k]


def format_hits(chunks: list[KnowledgeChunk]) -> str:
    if not chunks:
        return ""
    blocks = []
    for chunk in chunks:
        blocks.append(f"### p.{chunk.page} {chunk.title} ({chunk.id})\n{chunk.text}")
    return "\n\n".join(blocks)


def _score(query: str, chunk: KnowledgeChunk) -> float:
    tokens = {part for part in query.lower().replace("/", " ").split() if len(part) > 2}
    if not tokens:
        return 0.0
    haystack = f"{chunk.title} {chunk.text} {chunk.source_id}".lower()
    hits = sum(1 for token in tokens if token in haystack)
    return hits / len(tokens)

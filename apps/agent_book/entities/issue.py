"""Domain models for Agent Book knowledge and notes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    source_id: str
    source_path: str
    title: str
    text: str
    page: int = 0


@dataclass
class NoteDraft:
    topic: str
    claim: str
    evidence: str
    pages: list[int]
    chunk_ids: list[str]

    def to_record(self, note_key: str) -> dict:
        return {
            "note_key": note_key,
            "topic": self.topic,
            "claim": self.claim,
            "evidence": self.evidence,
            "pages": list(self.pages),
            "chunk_ids": list(self.chunk_ids),
        }

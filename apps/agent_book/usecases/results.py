"""Typed agent payloads — JSON at the MCP/CLI boundary via as_dict()."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from entities.issue import KnowledgeChunk


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    page: int
    title: str


@dataclass
class AgentTrace:
    steps: list[str]
    search_query: str = ""
    chunk_ids: list[str] = field(default_factory=list)
    followup: bool = False
    routed: str | None = None
    prompt_id: str = ""
    prompt_sha: str = ""
    elapsed_ms: int = 0
    tokens_in: int | None = None
    tokens_out: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AskResult:
    question: str
    answer: str
    citations: list[Citation]
    covered: bool
    offer_example: bool = False
    prompt_id: str = ""
    prompt_sha: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NoteResult:
    topic: str
    covered: bool
    prompt_id: str = ""
    prompt_sha: str = ""
    note_key: str = ""
    uri: str = ""
    pages: list[int] = field(default_factory=list)
    claim: str = ""
    evidence: str = ""
    answer: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExampleResult:
    topic: str
    scenario: str
    citations: list[Citation]
    covered: bool
    prompt_id: str = ""
    prompt_sha: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuoteResult:
    query: str
    passages: list[dict[str, Any]]
    citations: list[Citation]
    covered: bool
    prompt_id: str = ""
    prompt_sha: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FeedbackResult:
    recorded: bool
    prompt_id: str = ""
    prompt_sha: str = ""
    positive: bool = True
    reason: str = ""
    profile: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


ToolResult = AskResult | NoteResult | ExampleResult | QuoteResult | FeedbackResult


def citations_of(hits: list[KnowledgeChunk]) -> list[Citation]:
    return [Citation(hit.id, hit.page, hit.title) for hit in hits]


def as_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "as_dict"):
        return value.as_dict()
    return dict(value)


def merge_trace(payload: dict[str, Any], trace: AgentTrace) -> dict[str, Any]:
    result = dict(payload)
    result["trace"] = trace.as_dict()
    result["steps"] = trace.steps
    result["search_query"] = trace.search_query
    result["followup"] = trace.followup
    if trace.routed:
        result["routed"] = trace.routed
    if trace.prompt_id and "prompt_id" not in result:
        result["prompt_id"] = trace.prompt_id
        result["prompt_sha"] = trace.prompt_sha
    return result

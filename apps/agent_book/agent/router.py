"""Map a free-form chat message to one book tool via the LLM prompt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from connectors.llm import EchoLlm, LlmClient
from entities.system import ROUTE_PROMPT
from usecases.payload import as_object

BookTool = Literal["ask", "note", "example", "quote"]
AgentTool = Literal["ask", "note", "example", "quote", "feedback"]

BOOK_TOOLS: tuple[BookTool, ...] = ("ask", "note", "example", "quote")
AGENT_TOOLS: tuple[AgentTool, ...] = (*BOOK_TOOLS, "feedback")


@dataclass(frozen=True)
class RouteDecision:
    tool: AgentTool
    query: str
    feedback_positive: bool = False


def route_message(
    llm: LlmClient,
    message: str,
    last_query: str = "",
) -> RouteDecision:
    text = (message or "").strip()
    if not text:
        return RouteDecision(tool="ask", query="")
    if isinstance(llm, EchoLlm):
        return RouteDecision(tool="ask", query=text)
    user = f"User message: {text}"
    if last_query.strip():
        user += f"\nPrevious topic: {last_query.strip()}"
    parsed = parse_route_payload(llm.complete(system=ROUTE_PROMPT, user=user))
    if parsed is None:
        return RouteDecision(tool="ask", query=text)
    if parsed.tool != "feedback" and not parsed.query:
        return RouteDecision(
            tool=parsed.tool,
            query=text,
            feedback_positive=parsed.feedback_positive,
        )
    return parsed


def parse_route_payload(text: str) -> RouteDecision | None:
    payload = as_object(text)
    if payload is None:
        return None
    tool = str(payload.get("tool") or "").strip().lower()
    if not is_agent_tool(tool):
        return None
    query = str(payload.get("query") or "").strip()
    feedback = payload.get("feedback_positive")
    if isinstance(feedback, str):
        feedback_positive = feedback.strip().lower() in {"true", "1", "yes", "sim"}
    else:
        feedback_positive = bool(feedback)
    if tool == "feedback":
        return RouteDecision(tool="feedback", query=query, feedback_positive=True)
    return RouteDecision(
        tool=tool,  # type: ignore[arg-type]
        query=query,
        feedback_positive=feedback_positive,
    )


def bind_followup_query(query: str, last_query: str) -> tuple[str, bool]:
    """Echo / short replies: prefix the last topic when the message has no topic of its own."""
    current = (query or "").strip()
    prior = (last_query or "").strip()
    if not current or not prior:
        return current, False
    if prior.lower() in current.lower():
        return current, current.lower() != prior.lower() and _looks_underspecified(current)
    if not _looks_underspecified(current):
        return current, False
    return f"{prior}. {current}".strip()[:500], True


def is_followup(query: str, last_query: str) -> bool:
    current = (query or "").strip()
    prior = (last_query or "").strip()
    if not current or not prior:
        return False
    if prior.lower() in current.lower() and current.lower() != prior.lower():
        return _looks_underspecified(current)
    return _looks_underspecified(current)


def _looks_underspecified(query: str) -> bool:
    text = query.strip()
    lowered = text.lower()
    words = [part for part in lowered.replace("?", " ").split() if part]
    if not words:
        return False
    if lowered.startswith(("e ", "and ", "também ", "tambem ")):
        return True
    if "?" in text and len(words) >= 4:
        return False
    return len(words) <= 4


def is_book_tool(name: str) -> bool:
    return name in BOOK_TOOLS


def is_agent_tool(name: str) -> bool:
    return name in AGENT_TOOLS

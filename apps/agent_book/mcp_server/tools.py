"""Agent Book MCP tool bodies — no MCP SDK import (CI/tests stay light)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
_READY = False
_AGENT = None


def reset() -> None:
    """Drop cached process state so tests can swap lake roots."""
    global _READY, _AGENT
    _READY = False
    _AGENT = None


def ask_book(question: str) -> dict[str, Any]:
    return _call("ask", question)


def note_book(topic: str) -> dict[str, Any]:
    return _call("note", topic)


def example_book(topic: str) -> dict[str, Any]:
    return _call("example", topic)


def quote_book(query: str) -> dict[str, Any]:
    return _call("quote", query)


def chat_book(message: str) -> dict[str, Any]:
    return _call("chat", message)


def feedback_book(comment: str = "", positive: bool = True) -> dict[str, Any]:
    return _call("feedback", comment, positive=positive)


def _call(task: str, query: str, **kwargs: Any) -> dict[str, Any]:
    _prepare()
    global _AGENT
    from agent.agent_book import AgentBook

    if _AGENT is None:
        _AGENT = AgentBook()
    return _AGENT.invoke(task=task, query=query, **kwargs)


def _prepare() -> None:
    global _READY
    if _READY:
        return
    import sys

    from dotenv import load_dotenv

    from dataplatform.bootstrap import bootstrap

    load_dotenv(REPO_ROOT / ".env")
    for path in (REPO_ROOT, APP_ROOT):
        if path.is_dir() and str(path) not in sys.path:
            sys.path.insert(0, str(path))
    bootstrap("agent_book")
    _READY = True

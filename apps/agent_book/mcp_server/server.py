"""Agent Book MCP server — stdio tools for Cursor. Do not print to stdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
for _path in (REPO_ROOT, APP_ROOT):
    if _path.is_dir() and str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcp.server.mcpserver import MCPServer  # noqa: E402

from mcp_server.tools import (  # noqa: E402
    ask_book,
    chat_book,
    example_book,
    feedback_book,
    note_book,
    quote_book,
)


def build_server() -> MCPServer:
    server = MCPServer("agent_book")

    @server.tool()
    def agent_book_ask(question: str) -> str:
        """Answer from the book. Returns answer, pages, and offer_example."""
        return json.dumps(ask_book(question), ensure_ascii=False, default=str)

    @server.tool()
    def agent_book_note(topic: str) -> str:
        """Write a gold note (claim, evidence, pages) from the book and persist it."""
        return json.dumps(note_book(topic), ensure_ascii=False, default=str)

    @server.tool()
    def agent_book_example(topic: str) -> str:
        """Write a day-to-day scenario from the book."""
        return json.dumps(example_book(topic), ensure_ascii=False, default=str)

    @server.tool()
    def agent_book_quote(query: str) -> str:
        """Return raw book passages with pages. No paraphrase."""
        return json.dumps(quote_book(query), ensure_ascii=False, default=str)

    @server.tool()
    def agent_book_chat(message: str) -> str:
        """Interpret a free-form message and pick ask, note, example, quote, or feedback."""
        return json.dumps(chat_book(message), ensure_ascii=False, default=str)

    @server.tool()
    def agent_book_feedback(comment: str = "", positive: bool = True) -> str:
        """Record positive feedback so later answers match how the user likes them."""
        return json.dumps(
            feedback_book(comment=comment, positive=positive),
            ensure_ascii=False,
            default=str,
        )

    return server


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()

"""Local run — Agent Book agent tasks (ask, note, example, quote, chat, feedback)."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Book — agent tasks")
    sub = parser.add_subparsers(dest="task", required=True)

    ask = sub.add_parser("ask", help="answer from the book")
    ask.add_argument("--question", required=True)

    note = sub.add_parser("note", help="persist a gold note")
    note.add_argument("--topic", required=True)

    example = sub.add_parser("example", help="day-to-day scenario")
    example.add_argument("--topic", required=True)

    quote = sub.add_parser("quote", help="raw passages")
    quote.add_argument("--query", required=True)

    chat = sub.add_parser("chat", help="route a free-form message")
    chat.add_argument("--message", required=True)

    feedback = sub.add_parser("feedback", help="record positive feedback")
    feedback.add_argument("--comment", default="")
    feedback.add_argument("--negative", action="store_true")

    args = parser.parse_args()

    from dataplatform.bootstrap import bootstrap

    bootstrap("agent_book")
    from orchestrator.agent import (
        run_ask,
        run_chat,
        run_example,
        run_feedback,
        run_note,
        run_quote,
    )
    from workflows.orchestrator_base import log_result

    if args.task == "ask":
        result = run_ask(question=args.question)
    elif args.task == "note":
        result = run_note(topic=args.topic)
    elif args.task == "example":
        result = run_example(topic=args.topic)
    elif args.task == "quote":
        result = run_quote(query=args.query)
    elif args.task == "chat":
        result = run_chat(message=args.message)
    else:
        result = run_feedback(comment=args.comment, positive=not args.negative)
    log_result(args.task, result)


if __name__ == "__main__":
    main()

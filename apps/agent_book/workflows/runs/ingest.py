"""Local run — ingest the book into the Agent Book knowledge lake."""

from __future__ import annotations


def main() -> None:
    from dataplatform.bootstrap import bootstrap

    bootstrap("agent_book")
    from orchestrator.knowledge import run_ingest_book
    from workflows.orchestrator_base import log_result

    log_result("ingest_book", run_ingest_book())


if __name__ == "__main__":
    main()

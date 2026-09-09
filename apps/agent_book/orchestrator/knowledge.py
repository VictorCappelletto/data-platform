"""Knowledge process — ingest the book TXT."""

from __future__ import annotations

from typing import Any

from workflows.orchestrator_base import run_task


def run_ingest_book(**kwargs: Any) -> dict[str, Any]:
    from knowledge.ingest import run_ingest

    return run_task("ingest_book", run_ingest, **kwargs)

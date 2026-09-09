"""Extraction process — brewery API / fixture."""

from __future__ import annotations

from typing import Any

from workflows.orchestrator_base import run_task


def run_brewery_extract(**kwargs: Any) -> list[dict[str, Any]]:
    from extraction.brewery import run_extract

    return run_task("brewery_extract", run_extract, **kwargs)

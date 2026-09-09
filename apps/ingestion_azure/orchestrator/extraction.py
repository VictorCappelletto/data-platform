"""Extraction process — SQL Server → landing CSV."""

from __future__ import annotations

from typing import Any

from ingestion.landing_export import run_landing_export as _run_landing_export
from workflows.orchestrator_base import run_task


def run_landing_export(**kwargs: Any) -> dict[str, int]:
    return run_task("landing_export", _run_landing_export, **kwargs)

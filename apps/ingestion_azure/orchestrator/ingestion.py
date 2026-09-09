"""Ingestion process — legacy medallion domains (orders/customers JSON lake)."""

from __future__ import annotations

from typing import Any

from workflows.orchestrator_base import run_task


def run_orders(**kwargs: Any) -> dict[str, Any]:
    from ingestion.orders import run_pipeline

    return run_task("orders", run_pipeline, **kwargs)

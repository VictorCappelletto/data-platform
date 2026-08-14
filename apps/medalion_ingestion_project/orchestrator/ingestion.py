"""Ingestion process — brewery + orders medallion."""

from __future__ import annotations

from typing import Any

from workflows.orchestrator_base import run_task


def run_brewery_ingest(**kwargs: Any) -> dict[str, Any]:
    from ingestion.brewery import run_ingest_pipeline

    return run_task("brewery_ingest", run_ingest_pipeline, **kwargs)


def run_orders_landing(**kwargs: Any) -> str:
    from ingestion.orders import run_landing

    return run_task("orders_landing", run_landing, **kwargs)


def run_orders_bronze(**kwargs: Any) -> list[dict[str, Any]]:
    from ingestion.orders import run_bronze

    return run_task("orders_bronze", run_bronze, **kwargs)


def run_orders_silver(**kwargs: Any) -> list[dict[str, Any]]:
    from ingestion.orders import run_silver

    return run_task("orders_silver", run_silver, **kwargs)


def run_orders_pipeline(**kwargs: Any) -> dict[str, int]:
    from ingestion.orders import run_pipeline

    return run_task("orders_pipeline", run_pipeline, **kwargs)

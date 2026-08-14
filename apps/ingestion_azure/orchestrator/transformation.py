"""Transformation process — landing → processing → curated (+ Spark catalog)."""

from __future__ import annotations

from typing import Any

from transformation.olist import run_curated, run_sql_catalog, run_write_processing
from workflows.orchestrator_base import run_task


def run_processing(**kwargs: Any) -> dict[str, str]:
    return run_task("processing", run_write_processing, **kwargs)


def run_curated(**kwargs: Any) -> dict[str, Any]:
    return run_task("curated", run_curated, **kwargs)


def run_sql_catalog(**kwargs: Any) -> dict[str, Any]:
    return run_task("sql_catalog", run_sql_catalog, **kwargs)

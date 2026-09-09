"""Transformation process — landing → processing → curated (+ Spark catalog)."""

from __future__ import annotations

from typing import Any

from transformation import olist as olist_transform
from workflows.orchestrator_base import run_task


def run_processing(**kwargs: Any) -> dict[str, str]:
    return run_task("processing", olist_transform.run_write_processing, **kwargs)


def run_curated(**kwargs: Any) -> dict[str, Any]:
    return run_task("curated", olist_transform.run_curated, **kwargs)


def run_sql_catalog(**kwargs: Any) -> dict[str, Any]:
    return run_task("sql_catalog", olist_transform.run_sql_catalog, **kwargs)

"""Consumption process — lake → SQL Server olist_dw."""

from __future__ import annotations

from typing import Any

from consumption.sql_server_publish import run_publish_curated
from workflows.orchestrator_base import run_task


def run_publish_sql(**kwargs: Any) -> dict[str, Any]:
    return run_task("publish_sql", run_publish_curated, **kwargs)

"""Consumption process — analytics export."""

from __future__ import annotations

from typing import Any

from workflows.orchestrator_base import run_task


def run_analytics_export(**kwargs: Any) -> list[dict[str, Any]]:
    from consumption.analytics_export import run_export

    return run_task("analytics_export", run_export, **kwargs)

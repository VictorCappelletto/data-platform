"""Transformation process — brewery DQ/gold + orders KPIs."""

from __future__ import annotations

from typing import Any

from workflows.orchestrator_base import run_task


def run_brewery_dq_gold(**kwargs: Any) -> list[dict[str, Any]]:
    from transformation.brewery import run_dq_gold

    return run_task("brewery_dq_gold", run_dq_gold, **kwargs)


def run_kpi(**kwargs: Any) -> list[dict[str, Any]]:
    from transformation.kpi import run_kpi_pipeline

    return run_task("kpi", run_kpi_pipeline, **kwargs)

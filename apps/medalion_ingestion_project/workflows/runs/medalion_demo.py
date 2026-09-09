"""Local workflow — full medallion demos (orders + brewery)."""

from __future__ import annotations

import argparse
from typing import Any

from workflows.runs import consumption, ingestion, transformation


def run_orders_full(**kwargs: Any) -> dict[str, Any]:
    return {
        "task_id": "orders_full",
        "ingest": ingestion.run_orders(**kwargs),
        "kpis": transformation.run_kpi(**kwargs),
        "export": consumption.run(**kwargs),
    }


def run_brewery_full(**kwargs: Any) -> dict[str, Any]:
    from transformation.brewery import run_full_pipeline

    return {
        "task_id": "brewery_full",
        "pipeline": run_full_pipeline(**kwargs),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Medallion pipeline local runner")
    parser.add_argument(
        "--mode",
        choices=("orders_full", "brewery_full", "ingest_orders", "kpi", "export"),
        default="orders_full",
    )
    args = parser.parse_args()

    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID, log_result

    bootstrap(APP_ID)

    runners: dict[str, Any] = {
        "orders_full": run_orders_full,
        "brewery_full": run_brewery_full,
        "ingest_orders": ingestion.run_orders,
        "kpi": transformation.run_kpi,
        "export": consumption.run,
    }
    log_result(f"medalion_demo_{args.mode}", runners[args.mode]())


if __name__ == "__main__":
    main()

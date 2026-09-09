"""Local workflow — full medallion demos (orders + brewery)."""

from __future__ import annotations

import argparse
import os
from typing import Any

APP_ID = "medalion_ingestion_project"


def _apply_bulk_seeds() -> None:
    from dataplatform.config import ConfigLoader

    bulk = ConfigLoader(app=APP_ID).constants().get("seeds", {}).get("bulk", {})
    if orders := bulk.get("orders"):
        os.environ["ORDERS_SEED_PATH"] = orders
    if brewery := bulk.get("brewery"):
        os.environ["BREWERY_USE_FIXTURE"] = "1"
        os.environ["BREWERY_FIXTURE_PATH"] = brewery


def run_orders_full() -> dict[str, Any]:
    from workflows.runs import consumption, ingestion, transformation

    return {
        "task_id": "orders_full",
        "ingest": ingestion.run_orders(),
        "kpis": transformation.run_kpi(),
        "export": consumption.run(),
    }


def run_brewery_full(**kwargs: Any) -> dict[str, Any]:
    from transformation.brewery import run_full_pipeline

    return {"task_id": "brewery_full", "pipeline": run_full_pipeline(**kwargs)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Medallion pipeline local runner")
    parser.add_argument(
        "--mode",
        choices=("orders_full", "brewery_full", "ingest_orders", "kpi", "export"),
        default="orders_full",
    )
    parser.add_argument(
        "--bulk",
        action="store_true",
        help="Use bulk seeds from config/constants.yml",
    )
    args = parser.parse_args()

    from dataplatform.bootstrap import bootstrap

    bootstrap(APP_ID)

    if args.bulk:
        _apply_bulk_seeds()

    from workflows.orchestrator_base import log_result

    if args.mode == "ingest_orders":
        from workflows.runs import ingestion

        result = ingestion.run_orders()
    elif args.mode == "kpi":
        from workflows.runs import transformation

        result = transformation.run_kpi()
    elif args.mode == "export":
        from workflows.runs import consumption

        result = consumption.run()
    elif args.mode == "orders_full":
        result = run_orders_full()
    else:
        result = run_brewery_full()

    log_result(f"medalion_demo_{args.mode}", result)


if __name__ == "__main__":
    main()

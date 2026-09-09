"""Local workflow — full Olist pipeline (composes 4 process runners)."""

from __future__ import annotations

import argparse
from typing import Any

from workflows.runs import consumption, extraction, transformation


def run_full(**kwargs: Any) -> dict[str, Any]:
    return {
        "task_id": "olist_full",
        "landing_export": extraction.run(**kwargs),
        "processing": transformation.run_processing(**kwargs),
        "curated": transformation.run_curated(**kwargs),
        "publish_sql": consumption.run(**kwargs),
    }


def run_from_landing(**kwargs: Any) -> dict[str, Any]:
    return {
        "task_id": "olist_from_landing",
        **transformation.run_from_landing(**kwargs),
        "publish_sql": consumption.run(**kwargs),
    }


def run_transform_from_landing(**kwargs: Any) -> dict[str, Any]:
    return {
        "task_id": "olist_transform_from_landing",
        **transformation.run_from_landing(**kwargs),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Olist pipeline local runner")
    parser.add_argument(
        "--mode",
        choices=("full", "from_landing", "transform_from_landing", "publish", "sql_catalog"),
        default="full",
    )
    args = parser.parse_args()

    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID, log_result

    bootstrap(APP_ID)

    runners: dict[str, Any] = {
        "full": run_full,
        "from_landing": run_from_landing,
        "transform_from_landing": run_transform_from_landing,
        "publish": lambda **kw: {"publish_sql": consumption.run(**kw)},
        "sql_catalog": lambda **kw: {"sql_catalog": transformation.run_sql_catalog(**kw)},
    }
    log_result(f"olist_demo_{args.mode}", runners[args.mode]())


if __name__ == "__main__":
    main()

"""Local run — transformation process (landing → processing → curated)."""

from __future__ import annotations

import argparse
from typing import Any

from orchestrator import transformation


def run_processing(**kwargs: Any) -> dict[str, str]:
    return transformation.run_processing(**kwargs)


def run_curated(**kwargs: Any) -> dict[str, Any]:
    return transformation.run_curated(**kwargs)


def run_sql_catalog(**kwargs: Any) -> dict[str, Any]:
    return transformation.run_sql_catalog(**kwargs)


def run_from_landing(**kwargs: Any) -> dict[str, Any]:
    return {
        "processing": run_processing(**kwargs),
        "curated": run_curated(**kwargs),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Transformation process runner")
    parser.add_argument(
        "--mode",
        choices=("processing", "curated", "from_landing", "sql_catalog"),
        default="from_landing",
    )
    args = parser.parse_args()

    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID, log_result

    bootstrap(APP_ID)

    runners = {
        "processing": run_processing,
        "curated": run_curated,
        "from_landing": run_from_landing,
        "sql_catalog": run_sql_catalog,
    }
    log_result(f"transformation_{args.mode}", runners[args.mode]())


if __name__ == "__main__":
    main()

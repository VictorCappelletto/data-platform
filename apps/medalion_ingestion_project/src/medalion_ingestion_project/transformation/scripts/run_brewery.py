"""Run brewery DQ + gold transformation locally."""

from __future__ import annotations

from medalion_ingestion_project.runtime import bootstrap
from medalion_ingestion_project.transformation.brewery.pipeline import run_full_pipeline


def main() -> None:
    bootstrap()
    stats = run_full_pipeline()
    print({"transformation": stats})


if __name__ == "__main__":
    main()

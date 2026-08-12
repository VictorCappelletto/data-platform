"""Run orders ingestion locally (landing → bronze → silver)."""

from __future__ import annotations

from medalion_ingestion_project.ingestion.orders.pipeline import run_pipeline
from medalion_ingestion_project.runtime import bootstrap


def main() -> None:
    bootstrap()
    stats = run_pipeline()
    print({"ingestion": stats})


if __name__ == "__main__":
    main()

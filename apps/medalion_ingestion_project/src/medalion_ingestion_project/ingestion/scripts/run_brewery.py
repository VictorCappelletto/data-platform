"""Run brewery ingestion locally (landing → bronze → silver)."""

from __future__ import annotations

from medalion_ingestion_project.ingestion.brewery.pipeline import run_ingest_pipeline
from medalion_ingestion_project.runtime import bootstrap


def main() -> None:
    bootstrap()
    stats = run_ingest_pipeline()
    print({"ingestion": stats})


if __name__ == "__main__":
    main()

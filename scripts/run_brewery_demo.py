"""Local helper to run the full brewery demo without Airflow."""

from __future__ import annotations


def main() -> None:
    from medalion_ingestion_project.runtime import bootstrap
    from medalion_ingestion_project.transformation.brewery.pipeline import run_full_pipeline

    bootstrap()
    stats = run_full_pipeline()
    print(stats)


if __name__ == "__main__":
    main()

"""Run analytics export locally."""

from __future__ import annotations

from medalion_ingestion_project.runtime import bootstrap
from medalion_ingestion_project.transformation.export import run_export


def main() -> None:
    bootstrap()
    exported = run_export()
    print({"export_rows": len(exported)})


if __name__ == "__main__":
    main()

"""Run brewery ETL demo using local fixture (no HTTP)."""

from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault("LAKE_ROOT", str(root / "data" / "lake"))
    os.environ.setdefault("PLATFORM_ENV", "local")
    os.environ.setdefault("LAKE_BACKEND", "local")

    from brewery_etl.pipelines import run_full_pipeline

    fixture = root / "seeds" / "breweries_sample.json"
    stats = run_full_pipeline(fixture_path=str(fixture))
    print(stats)


if __name__ == "__main__":
    main()

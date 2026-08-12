"""Run brewery extraction locally."""

from __future__ import annotations

from medalion_ingestion_project.extraction.brewery import BreweryExtractor
from medalion_ingestion_project.runtime import bootstrap


def main() -> None:
    bootstrap()
    rows = BreweryExtractor().extract()
    print({"extracted_rows": len(rows)})


if __name__ == "__main__":
    main()

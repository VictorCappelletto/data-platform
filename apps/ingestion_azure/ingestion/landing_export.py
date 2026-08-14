"""SQL Server → landing CSV for all Olist tables (ADF copy equivalent)."""

from __future__ import annotations

from typing import Any

from extraction.base import SqlExtractionBase
from transformation.io import OlistLakeMount


class LandingExporter(SqlExtractionBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("olist", environment)
        self.mount = OlistLakeMount(
            lake_prefix=self.app.lake_prefix,
            environment=self.platform.environment,
        )
        self.schema = self.product_config.get("schema", "dbo")
        self.tables = list(self.product_config.get("tables", []))

    def export_table(self, table: str) -> tuple[str, int]:
        source = f"{self.schema}.{table}"
        rows = self.fetch_table(source)
        path = self.mount.file_path("landing", f"{table}.csv")
        self.mount.write_csv(path, rows)
        self.logger.info("landing csv %s: %s rows -> %s", table, len(rows), path)
        return path, len(rows)

    def run(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for table in self.tables:
            _, count = self.export_table(table)
            counts[table] = count
        return counts


def run_landing_export(**_kwargs: Any) -> dict[str, int]:
    """Orchestrator entry point."""
    return LandingExporter().run()

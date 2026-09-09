"""SQL Server extraction — shared base for extraction process."""

from __future__ import annotations

from typing import Any

from dataplatform.process_base import ProjectProcessBase
from utils.settings import bind_azure_settings


class SqlExtractionBase(ProjectProcessBase):
    def __init__(self, domain_key: str, environment: str | None = None) -> None:
        super().__init__("extraction", domain_key, environment)
        bind_azure_settings(self, environment)

    @property
    def sql(self):
        return self.app.sql_server

    @property
    def source_table(self) -> str:
        return self.product_config["source_table"]

    def fetch_table(self, table: str) -> list[dict[str, Any]]:
        """Read all rows from a SQL Server table or view."""
        query = f"SELECT * FROM {table}"
        try:
            import pyodbc
        except ImportError as exc:
            raise RuntimeError(
                "pyodbc is required for SQL extraction. Install with: pip install pyodbc"
            ) from exc

        rows: list[dict[str, Any]] = []
        with pyodbc.connect(self.sql.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            for record in cursor.fetchall():
                rows.append(dict(zip(columns, record, strict=True)))
        return rows

    def extract(self) -> list[dict[str, Any]]:
        """Pull rows from the domain source_table in config."""
        self.logger.info("extracting from %s", self.source_table)
        return self.fetch_table(self.source_table)

    def run(self) -> list[dict[str, Any]]:
        rows = self.extract()
        self.logger.info("%s extraction complete: %s rows", self.domain_key, len(rows))
        return rows

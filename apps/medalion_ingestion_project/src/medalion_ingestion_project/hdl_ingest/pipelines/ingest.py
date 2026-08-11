from __future__ import annotations

from typing import Any

from medalion_ingestion_project.base import ProjectProductBase
from medalion_ingestion_project.hdl_ingest.tables.orders import OrdersTable

from dataplatform.dbutils.paths import Layer


class HdlIngestPipeline(ProjectProductBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("hdl_ingest", environment)

    @property
    def domain(self) -> str:
        return self.product_config["domain"]

    @property
    def table(self) -> str:
        return self.product_config["table"]

    def run_landing(self, seed_csv: str | None = None) -> str:
        seed = seed_csv or str(
            self.loader.resolve_project_path(self.product_config["seed_path"])
        )
        rows = self.io.read_csv(seed)
        dest = self.paths.table_path(Layer.LANDING, self.domain, self.table)
        written = self.io.write_csv(dest, rows)
        self.logger.info("landing ready: %s (%s rows)", written, len(rows))
        return written

    def run_bronze(self, landing_path: str | None = None) -> list[dict[str, Any]]:
        source = landing_path or self.paths.table_path(Layer.LANDING, self.domain, self.table)
        raw = self.io.read_csv(source)
        bronze = OrdersTable().to_bronze(raw)
        dest = self.paths.table_path(Layer.BRONZE, self.domain, self.table)
        self.io.write_json(dest, bronze)
        self.logger.info("bronze ready: %s rows", len(bronze))
        return bronze

    def run_silver(self, bronze_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        if bronze_rows is None:
            bronze_rows = self.io.read_json(
                self.paths.table_path(Layer.BRONZE, self.domain, self.table)
            )
        silver = OrdersTable().to_silver(bronze_rows)
        dest = self.paths.table_path(Layer.SILVER, self.domain, self.table)
        self.io.write_json(dest, silver)
        current = sum(1 for r in silver if r.get("is_current"))
        self.logger.info("silver ready: %s rows (%s current)", len(silver), current)
        return silver

    def run_pipeline(self, seed_csv: str | None = None) -> dict[str, int]:
        self.run_landing(seed_csv)
        bronze = self.run_bronze()
        silver = self.run_silver(bronze)
        return {
            "bronze_rows": len(bronze),
            "silver_rows": len(silver),
            "current_rows": sum(1 for r in silver if r.get("is_current")),
        }


def run_landing(**_kwargs: Any) -> str:
    return HdlIngestPipeline().run_landing()


def run_bronze(**_kwargs: Any) -> list[dict[str, Any]]:
    return HdlIngestPipeline().run_bronze()


def run_silver(**_kwargs: Any) -> list[dict[str, Any]]:
    return HdlIngestPipeline().run_silver()


def run_pipeline(seed_csv: str | None = None, **_kwargs: Any) -> dict[str, int]:
    return HdlIngestPipeline().run_pipeline(seed_csv)

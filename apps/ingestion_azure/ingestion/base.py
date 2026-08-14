"""Shared helpers for ingestion stage (SQL → medallion lake)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from dataplatform.process_base import ProjectProcessBase
from dataplatform.lake import Layer
from extraction.base import SqlExtractionBase
from utils.settings import bind_azure_settings


class IngestionBase(ProjectProcessBase, ABC):
    def __init__(self, domain_key: str, environment: str | None = None) -> None:
        super().__init__("ingestion", domain_key, environment)
        bind_azure_settings(self, environment)

    @property
    def domain(self) -> str:
        return self.product_config["domain"]

    @property
    def table(self) -> str:
        return self.product_config["table"]

    @property
    def source_table(self) -> str:
        return self.product_config["source_table"]

    def layer_path(self, layer: Layer | str) -> str:
        return self.paths.table_path(layer, self.domain, self.table)

    def write_landing_json(self, rows: list[dict[str, Any]]) -> str:
        dest = self.layer_path(Layer.LANDING)
        written = self.io.write_json(dest, rows)
        self.logger.info("landing ready: %s (%s rows)", written, len(rows))
        return written

    def read_from_sql(self) -> list[dict[str, Any]]:
        return SqlExtractionBase(self.domain_key).fetch_table(self.source_table)

    @abstractmethod
    def to_bronze(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Entity-specific bronze normalization."""

    def run_landing(self) -> str:
        rows = self.read_from_sql()
        return self.write_landing_json(rows)

    def run_bronze(self, landing_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        if landing_rows is None:
            landing_rows = self.io.read_json(self.layer_path(Layer.LANDING))
        bronze = self.to_bronze(landing_rows)
        self.io.write_json(self.layer_path(Layer.BRONZE), bronze)
        self.logger.info("bronze ready: %s rows", len(bronze))
        return bronze

    def run_pipeline(self) -> dict[str, int]:
        self.run_landing()
        bronze = self.run_bronze()
        return {"landing_rows": len(bronze), "bronze_rows": len(bronze)}

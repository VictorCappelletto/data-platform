"""Shared helpers for ingestion stage pipelines (medallion landing → silver)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from dataplatform.lake import Layer, LayerPaths
from dataplatform.process_base import ProjectProcessBase
from dataplatform.utils import utc_today
from utils.settings import bind_medalion_settings


class IngestionBase(ProjectProcessBase, ABC):
    """Base for table-scoped medallion ingestion."""

    def __init__(self, domain_key: str, environment: str | None = None) -> None:
        super().__init__("ingestion", domain_key, environment)
        bind_medalion_settings(self, environment)

    @property
    def domain(self) -> str:
        return self.product_config["domain"]

    @property
    def table(self) -> str:
        return self.product_config["table"]

    def layer_path(self, layer: Layer | str) -> str:
        return self.paths.table_path(layer, self.domain, self.table)

    def resolve_seed_path(self, seed_csv: str | None = None) -> str:
        if seed_csv:
            return seed_csv
        return str(self.loader.resolve_project_path(self.product_config["seed_path"]))

    def write_landing_csv(self, rows: list[dict[str, Any]]) -> str:
        dest = self.layer_path(Layer.LANDING)
        written = self.io.write_csv(dest, rows)
        self.logger.info("landing ready: %s (%s rows)", written, len(rows))
        return written

    def read_landing_csv(self, landing_path: str | None = None) -> list[dict[str, Any]]:
        source = landing_path or self.layer_path(Layer.LANDING)
        return self.io.read_csv(source)

    def write_layer_json(self, layer: Layer | str, rows: list[dict[str, Any]]) -> None:
        dest = self.layer_path(layer)
        self.io.write_json(dest, rows)

    def read_layer_json(self, layer: Layer | str) -> list[dict[str, Any]]:
        return self.io.read_json(self.layer_path(layer))

    @staticmethod
    def dedupe_by_id(rows: list[dict[str, Any]], column: str = "id") -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = row.get(column)
            if key:
                by_id[key] = row
        return list(by_id.values())

    @abstractmethod
    def to_bronze(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Entity-specific bronze normalization."""

    @abstractmethod
    def to_silver(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Entity-specific silver rules (dedup, SCD, etc.)."""

    def run_landing(self, seed_csv: str | None = None) -> str:
        rows = self.io.read_csv(self.resolve_seed_path(seed_csv))
        return self.write_landing_csv(rows)

    def run_bronze(self, landing_path: str | None = None) -> list[dict[str, Any]]:
        raw = self.read_landing_csv(landing_path)
        bronze = self.to_bronze(raw)
        self.write_layer_json(Layer.BRONZE, bronze)
        self.logger.info("bronze ready: %s rows", len(bronze))
        return bronze

    def run_silver(self, bronze_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        if bronze_rows is None:
            bronze_rows = self.read_layer_json(Layer.BRONZE)
        silver = self.to_silver(bronze_rows)
        self.write_layer_json(Layer.SILVER, silver)
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


class PartitionedIngestionBase(IngestionBase):
    """Ingestion base for country/state/load_date partitioned domains."""

    @staticmethod
    def load_date(value: date | None = None) -> str:
        return (value or utc_today()).isoformat()

    @staticmethod
    def partition_key(record: dict) -> tuple[str, str]:
        country = (record.get("country") or "unknown").strip().upper() or "UNKNOWN"
        state = (record.get("state") or record.get("state_province") or "unknown").strip().upper()
        state = state.replace(" ", "_") or "UNKNOWN"
        return country, state

    @staticmethod
    def partition_path(
        layer: Layer | str,
        *,
        country: str,
        state: str,
        load_dt: str,
        paths: LayerPaths,
        domain: str = "brewery",
        table: str = "breweries",
    ) -> str:
        table_base = paths.table_path(layer, domain, table)
        suffix = f"country={country}/state={state}/load_date={load_dt}"
        if paths.backend in {"s3", "minio"}:
            return f"{table_base}/{suffix}"
        return str((Path(table_base) / suffix).as_posix())

    def write_partitions(
        self,
        rows: list[dict[str, Any]],
        layer: Layer | str,
        load_dt: str,
    ) -> int:
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[self.partition_key(row)].append(row)
        written = 0
        for (country, state), part_rows in groups.items():
            dest = self.partition_path(
                layer,
                country=country,
                state=state,
                load_dt=load_dt,
                paths=self.paths,
                domain=self.domain,
                table=self.table,
            )
            self.io.write_json(dest, part_rows)
            written += len(part_rows)
        return written

    def read_layer_partitions(self, layer: Layer | str, load_dt: str) -> list[dict[str, Any]]:
        base = self.layer_path(layer)
        if self.paths.backend in {"s3", "minio"}:
            raise NotImplementedError("partition read for s3 backend not implemented in v1")
        root = Path(base)
        rows: list[dict[str, Any]] = []
        for file_path in root.glob(f"**/load_date={load_dt}/data.json"):
            rows.extend(self.io.read_json(str(file_path)))
        return rows

    def run_landing(
        self,
        *,
        load_dt: str | None = None,
        fixture_path: str | None = None,
        landing_rows: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        load_dt = load_dt or self.load_date()
        if landing_rows is not None:
            raw = landing_rows
        else:
            raw = self.extract_rows(fixture_path=fixture_path)
        self.write_partitions(raw, Layer.LANDING, load_dt)
        self.logger.info("landing complete: %s rows load_date=%s", len(raw), load_dt)
        return raw

    def run_bronze(
        self,
        *,
        load_dt: str | None = None,
        landing_rows: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        load_dt = load_dt or self.load_date()
        if landing_rows is None:
            landing_rows = self.read_layer_partitions(Layer.LANDING, load_dt)
        bronze = self.to_bronze(landing_rows)
        self.write_partitions(bronze, Layer.BRONZE, load_dt)
        self.logger.info("bronze complete: %s rows", len(bronze))
        return bronze

    def run_silver(
        self,
        *,
        load_dt: str | None = None,
        bronze_rows: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        load_dt = load_dt or self.load_date()
        if bronze_rows is None:
            bronze_rows = self.read_layer_partitions(Layer.BRONZE, load_dt)
        silver = self.to_silver(bronze_rows)
        self.write_partitions(silver, Layer.SILVER, load_dt)
        self.logger.info("silver complete: %s rows (deduped)", len(silver))
        return silver

    def run_ingest_pipeline(
        self,
        *,
        fixture_path: str | None = None,
        load_dt: str | None = None,
    ) -> dict[str, Any]:
        load_dt = load_dt or self.load_date()
        landing = self.run_landing(load_dt=load_dt, fixture_path=fixture_path)
        bronze = self.run_bronze(load_dt=load_dt, landing_rows=landing)
        silver = self.run_silver(load_dt=load_dt, bronze_rows=bronze)
        return {
            "landing_rows": len(landing),
            "bronze_rows": len(bronze),
            "silver_rows": len(silver),
            "load_date": load_dt,
        }

    @abstractmethod
    def extract_rows(self, *, fixture_path: str | None = None) -> list[dict[str, Any]]:
        """Pull source rows before landing write."""

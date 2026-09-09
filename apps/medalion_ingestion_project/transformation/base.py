"""Shared helpers for transformation stage pipelines (silver → gold, export, DQ)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import Any

from dataplatform.data_quality import (
    CheckResult,
    null_rate,
    range_check,
    run_checks,
    volume_vs_baseline,
)
from dataplatform.lake import Layer
from dataplatform.process_base import ProjectProcessBase
from ingestion.base import PartitionedIngestionBase
from utils.settings import bind_medalion_settings


class TransformationBase(ProjectProcessBase, ABC):
    """Base for transformation-stage jobs."""

    def __init__(self, domain_key: str, environment: str | None = None) -> None:
        super().__init__("transformation", domain_key, environment)
        bind_medalion_settings(self, environment)

    @property
    def source_config(self) -> dict[str, Any]:
        return self.product_config.get("source", {})

    @property
    def target_config(self) -> dict[str, Any]:
        return self.product_config.get("target", {})

    def read_source_rows(self) -> list[dict[str, Any]]:
        source = self.source_config
        return self.io.read_json(
            self.paths.table_path(Layer(source["layer"]), source["domain"], source["table"])
        )

    def write_target_rows(self, rows: list[dict[str, Any]]) -> str:
        target = self.target_config
        dest = self.paths.table_path(Layer(target["layer"]), target["domain"], target["table"])
        return self.io.write_json(dest, rows)

    def run_null_checks(self, rows: list[dict[str, Any]], columns: list[str]) -> list[CheckResult]:
        return [null_rate(rows, col, max_rate=0.0) for col in columns]

    def run_standard_export_dq(
        self,
        rows: list[dict[str, Any]],
        *,
        null_columns: list[str],
        min_value: float,
        baseline_count: int,
        max_variance_pct: float,
    ) -> None:
        results = self.run_null_checks(rows, null_columns)
        results.append(range_check(rows, "kpi_value", min_value=min_value))
        results.append(
            volume_vs_baseline(len(rows), baseline_count, max_variance_pct=max_variance_pct)
        )
        run_checks(results)

    @abstractmethod
    def transform(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Domain-specific transformation logic."""

    def run(self, rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        source_rows = rows if rows is not None else self.read_source_rows()
        output = self.transform(source_rows)
        self.write_target_rows(output)
        self.logger.info("%s transform complete: %s rows", self.domain_key, len(output))
        return output


class PartitionedTransformationBase(TransformationBase):
    """Transformation base for country/state/load_date partitioned domains (brewery)."""

    load_date = staticmethod(PartitionedIngestionBase.load_date)
    partition_key = staticmethod(PartitionedIngestionBase.partition_key)
    partition_path = staticmethod(PartitionedIngestionBase.partition_path)

    def __init__(
        self,
        domain_key: str,
        environment: str | None = None,
        *,
        ingestion_domain: str = "brewery",
        ingestion_table: str = "breweries",
    ) -> None:
        super().__init__(domain_key, environment)
        self._domain = ingestion_domain
        self._table = ingestion_table

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def table(self) -> str:
        return self._table

    def layer_path(self, layer: Layer | str) -> str:
        return self.paths.table_path(layer, self.domain, self.table)

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

    def duplicate_ids(self, rows: list[dict[str, Any]], column: str = "id") -> CheckResult:
        ids = [r.get(column) for r in rows if r.get(column)]
        dupes = len(ids) - len(set(ids))
        return CheckResult(
            name=f"duplicate:{column}",
            passed=dupes == 0,
            message=f"duplicate_count={dupes}",
            metrics={"rows": len(rows), "duplicates": dupes},
        )

    def check_min_volume(self, rows: list[dict[str, Any]]) -> CheckResult:
        minimum = int(self.product_config["dq"]["min_volume"])
        count = len(rows)
        return CheckResult(
            name="min_volume",
            passed=count >= minimum,
            message=f"count={count} min={minimum}",
            metrics={"count": count, "minimum": minimum},
        )

    def run_dq_checks(self, rows: list[dict[str, Any]]) -> None:
        dq_cfg = self.product_config["dq"]
        results = self.run_null_checks(rows, dq_cfg["null_columns"])
        if dq_cfg.get("check_duplicates", True):
            results.append(self.duplicate_ids(rows, "id"))
        results.append(self.check_min_volume(rows))
        run_checks(results)

    def run_dq_gold(self, *, load_dt: str | None = None) -> list[dict[str, Any]]:
        load_dt = load_dt or self.load_date()
        silver = self.read_layer_partitions(Layer.SILVER, load_dt)
        self.run_dq_checks(silver)
        gold = self.transform(silver)
        self.write_partitions(gold, Layer.GOLD, load_dt)
        self.logger.info("gold complete: %s rows after DQ", len(gold))
        return gold

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from dataplatform.dbutils.paths import Layer
from dataplatform.dq import CheckResult, null_rate, run_checks
from medalion_ingestion_project.base import ProjectProcessBase
from medalion_ingestion_project.ingestion.brewery.partition import (
    load_date,
    partition_key,
    partition_path,
)


class BreweryTransformPipeline(ProjectProcessBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("transformation", "brewery", environment)
        ingestion_cfg = self.loader.process("ingestion", environment).get("brewery", {})
        self._domain = ingestion_cfg.get("domain", "brewery")
        self._table = ingestion_cfg.get("table", "breweries")

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def table(self) -> str:
        return self._table

    def _write_partitions(
        self,
        rows: list[dict[str, Any]],
        layer: Layer,
        load_dt: str,
    ) -> int:
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[partition_key(row)].append(row)
        written = 0
        for (country, state), part_rows in groups.items():
            dest = partition_path(
                layer,
                country=country,
                state=state,
                load_dt=load_dt,
                paths=self.paths,
            )
            self.io.write_json(dest, part_rows)
            written += len(part_rows)
        return written

    def _read_layer_partitions(self, layer: Layer, load_dt: str) -> list[dict[str, Any]]:
        base = self.paths.table_path(layer, self.domain, self.table)
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
        ok = dupes == 0
        return CheckResult(
            name=f"duplicate:{column}",
            passed=ok,
            message=f"duplicate_count={dupes}",
            metrics={"rows": len(rows), "duplicates": dupes},
        )

    def check_min_volume(self, rows: list[dict[str, Any]]) -> CheckResult:
        minimum = int(self.product_config["dq"]["min_volume"])
        count = len(rows)
        ok = count >= minimum
        return CheckResult(
            name="min_volume",
            passed=ok,
            message=f"count={count} min={minimum}",
            metrics={"count": count, "minimum": minimum},
        )

    def run_dq_gold(self, *, load_dt: str | None = None) -> list[dict[str, Any]]:
        load_dt = load_dt or load_date()
        silver = self._read_layer_partitions(Layer.SILVER, load_dt)
        dq_cfg = self.product_config["dq"]
        results = [
            null_rate(silver, col, max_rate=0.0) for col in dq_cfg["null_columns"]
        ]
        if dq_cfg.get("check_duplicates", True):
            results.append(self.duplicate_ids(silver, "id"))
        results.append(self.check_min_volume(silver))
        run_checks(results)

        gold = silver
        self._write_partitions(gold, Layer.GOLD, load_dt)
        self.logger.info("gold complete: %s rows after DQ", len(gold))
        return gold

    def run_full_pipeline(
        self,
        *,
        fixture_path: str | None = None,
        load_dt: str | None = None,
    ) -> dict[str, Any]:
        from medalion_ingestion_project.ingestion.brewery.pipeline import BreweryIngestPipeline

        stats = BreweryIngestPipeline().run_ingest_pipeline(
            fixture_path=fixture_path,
            load_dt=load_dt,
        )
        gold = self.run_dq_gold(load_dt=stats["load_date"])
        stats["gold_rows"] = len(gold)
        return stats


def duplicate_ids(rows: list[dict[str, Any]], column: str = "id") -> CheckResult:
    return BreweryTransformPipeline().duplicate_ids(rows, column)


def run_dq_gold(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryTransformPipeline().run_dq_gold(load_dt=kwargs.get("load_dt"))


def run_full_pipeline(**kwargs: Any) -> dict[str, Any]:
    return BreweryTransformPipeline().run_full_pipeline(
        fixture_path=kwargs.get("fixture_path"),
        load_dt=kwargs.get("load_dt"),
    )

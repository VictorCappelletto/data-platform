from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from medalion_ingestion_project.base import ProjectProductBase
from medalion_ingestion_project.brewery_etl.extract import BreweryExtractor
from medalion_ingestion_project.brewery_etl.partition import (
    load_date,
    partition_key,
    partition_path,
)
from medalion_ingestion_project.brewery_etl.transform import transform_breweries

from dataplatform.dbutils.paths import Layer
from dataplatform.dq import CheckResult, null_rate, run_checks


class BreweryPipeline(ProjectProductBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("brewery_etl", environment)
        self.extractor = BreweryExtractor(environment)

    @property
    def domain(self) -> str:
        return self.product_config["domain"]

    @property
    def table(self) -> str:
        return self.product_config["table"]

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

    def run_landing(
        self,
        *,
        load_dt: str | None = None,
        fixture_path: str | None = None,
    ) -> list[dict[str, Any]]:
        load_dt = load_dt or load_date()
        raw = self.extractor.extract(fixture_path=fixture_path)
        self._write_partitions(raw, Layer.LANDING, load_dt)
        self.logger.info("landing complete: %s rows load_date=%s", len(raw), load_dt)
        return raw

    def run_bronze(
        self,
        *,
        load_dt: str | None = None,
        landing_rows: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        load_dt = load_dt or load_date()
        if landing_rows is None:
            landing_rows = self._read_layer_partitions(Layer.LANDING, load_dt)
        bronze = transform_breweries(landing_rows)
        self._write_partitions(bronze, Layer.BRONZE, load_dt)
        self.logger.info("bronze complete: %s rows", len(bronze))
        return bronze

    def run_silver(
        self,
        *,
        load_dt: str | None = None,
        bronze_rows: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        load_dt = load_dt or load_date()
        if bronze_rows is None:
            bronze_rows = self._read_layer_partitions(Layer.BRONZE, load_dt)
        silver = self._dedupe_by_id(bronze_rows)
        self._write_partitions(silver, Layer.SILVER, load_dt)
        self.logger.info("silver complete: %s rows (deduped)", len(silver))
        return silver

    def _read_layer_partitions(self, layer: Layer, load_dt: str) -> list[dict[str, Any]]:
        base = self.paths.table_path(layer, self.domain, self.table)
        if self.paths.backend in {"s3", "minio"}:
            raise NotImplementedError("partition read for s3 backend not implemented in v1")
        root = Path(base)
        rows: list[dict[str, Any]] = []
        for file_path in root.glob(f"**/load_date={load_dt}/data.json"):
            rows.extend(self.io.read_json(str(file_path)))
        return rows

    @staticmethod
    def _dedupe_by_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = row.get("id")
            if key:
                by_id[key] = row
        return list(by_id.values())

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

    def run_ingest_pipeline(
        self,
        *,
        fixture_path: str | None = None,
        load_dt: str | None = None,
    ) -> dict[str, Any]:
        load_dt = load_dt or load_date()
        landing = self.run_landing(load_dt=load_dt, fixture_path=fixture_path)
        bronze = self.run_bronze(load_dt=load_dt, landing_rows=landing)
        silver = self.run_silver(load_dt=load_dt, bronze_rows=bronze)
        return {
            "landing_rows": len(landing),
            "bronze_rows": len(bronze),
            "silver_rows": len(silver),
            "load_date": load_dt,
        }

    def run_full_pipeline(
        self,
        *,
        fixture_path: str | None = None,
        load_dt: str | None = None,
    ) -> dict[str, Any]:
        stats = self.run_ingest_pipeline(fixture_path=fixture_path, load_dt=load_dt)
        gold = self.run_dq_gold(load_dt=stats["load_date"])
        stats["gold_rows"] = len(gold)
        return stats


def duplicate_ids(rows: list[dict[str, Any]], column: str = "id") -> CheckResult:
    return BreweryPipeline().duplicate_ids(rows, column)


def run_landing(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryPipeline().run_landing(
        load_dt=kwargs.get("load_dt"),
        fixture_path=kwargs.get("fixture_path"),
    )


def run_bronze(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryPipeline().run_bronze(
        load_dt=kwargs.get("load_dt"),
        landing_rows=kwargs.get("landing_rows"),
    )


def run_silver(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryPipeline().run_silver(
        load_dt=kwargs.get("load_dt"),
        bronze_rows=kwargs.get("bronze_rows"),
    )


def run_dq_gold(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryPipeline().run_dq_gold(load_dt=kwargs.get("load_dt"))


def run_ingest_pipeline(**_kwargs: Any) -> dict[str, Any]:
    return BreweryPipeline().run_ingest_pipeline()


def run_full_pipeline(**_kwargs: Any) -> dict[str, Any]:
    return BreweryPipeline().run_full_pipeline()

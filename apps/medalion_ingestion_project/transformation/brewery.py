"""Brewery transformation — silver → DQ → gold, plus full demo pipeline."""

from __future__ import annotations

from typing import Any

from ingestion.brewery import BreweryIngestPipeline
from transformation.base import PartitionedTransformationBase


class BreweryTransformPipeline(PartitionedTransformationBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("brewery", environment)
        ingestion_cfg = self.loader.process("ingestion", environment).get("brewery", {})
        self._domain = ingestion_cfg.get("domain", "brewery")
        self._table = ingestion_cfg.get("table", "breweries")

    def transform(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return rows

    def run_full_pipeline(
        self,
        *,
        fixture_path: str | None = None,
        load_dt: str | None = None,
    ) -> dict[str, Any]:
        stats = BreweryIngestPipeline().run_ingest_pipeline(
            fixture_path=fixture_path,
            load_dt=load_dt,
        )
        gold = self.run_dq_gold(load_dt=stats["load_date"])
        stats["gold_rows"] = len(gold)
        return stats


# Orchestrator entry points — referenced by config/orchestration/*.yml (domain_module).
def run_dq_gold(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryTransformPipeline().run_dq_gold(load_dt=kwargs.get("load_dt"))


def run_full_pipeline(**kwargs: Any) -> dict[str, Any]:
    return BreweryTransformPipeline().run_full_pipeline(
        fixture_path=kwargs.get("fixture_path"),
        load_dt=kwargs.get("load_dt"),
    )

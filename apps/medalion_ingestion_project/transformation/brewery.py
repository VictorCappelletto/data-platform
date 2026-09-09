"""Brewery transformation — silver → DQ → gold, plus full demo pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
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
        enrich = self.product_config.get("enrich", {})
        craft_types = {value.lower() for value in enrich.get("craft_types", [])}
        country_codes = enrich.get("country_codes", {})
        us_state_codes = enrich.get("us_state_codes", {})
        load_date = self._current_load_dt or self.load_date()
        processed_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        gold: list[dict[str, Any]] = []
        for row in rows:
            country = (row.get("country") or "").strip()
            state = (row.get("state") or row.get("state_province") or "").strip()
            brewery_type = (row.get("brewery_type") or "").strip().lower()
            country_code = country_codes.get(country)
            state_code = us_state_codes.get(state.title()) if country_code == "US" else None
            latitude = row.get("latitude")
            longitude = row.get("longitude")

            enriched = dict(row)
            enriched.update(
                {
                    "load_date": load_date,
                    "processed_at": processed_at,
                    "country_code": country_code,
                    "state_code": state_code,
                    "has_coordinates": latitude is not None and longitude is not None,
                    "is_craft": brewery_type in craft_types,
                }
            )
            gold.append(enriched)
        return gold

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


def run_dq_gold(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryTransformPipeline().run_dq_gold(load_dt=kwargs.get("load_dt"))


def run_full_pipeline(**kwargs: Any) -> dict[str, Any]:
    return BreweryTransformPipeline().run_full_pipeline(
        fixture_path=kwargs.get("fixture_path"),
        load_dt=kwargs.get("load_dt"),
    )

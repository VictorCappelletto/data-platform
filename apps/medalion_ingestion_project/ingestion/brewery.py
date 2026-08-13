"""Brewery ingestion — extract, transform, partition, landing → silver."""

from __future__ import annotations

from typing import Any

from extraction.brewery import BreweryExtractor
from ingestion.base import PartitionedIngestionBase


class BreweryIngestPipeline(PartitionedIngestionBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("brewery", environment)
        self._extractor = BreweryExtractor(environment)

    def extract_rows(self, *, fixture_path: str | None = None) -> list[dict[str, Any]]:
        return self._extractor.extract(fixture_path=fixture_path)

    def to_bronze(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        bronze = [self._normalize_record(row) for row in rows]
        self.logger.info("transformed %s records", len(bronze))
        return bronze

    def to_silver(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.dedupe_by_id(rows)

    @staticmethod
    def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": BreweryIngestPipeline._safe_str(record.get("id"), 200),
            "name": BreweryIngestPipeline._safe_str(record.get("name"), 255),
            "brewery_type": BreweryIngestPipeline._safe_str(record.get("brewery_type"), 100),
            "address_1": BreweryIngestPipeline._safe_str(record.get("address_1"), 255),
            "address_2": BreweryIngestPipeline._safe_str(record.get("address_2"), 255),
            "address_3": BreweryIngestPipeline._safe_str(record.get("address_3"), 255),
            "city": BreweryIngestPipeline._safe_str(record.get("city"), 100),
            "state_province": BreweryIngestPipeline._safe_str(record.get("state_province"), 100),
            "postal_code": BreweryIngestPipeline._safe_str(record.get("postal_code"), 50),
            "country": BreweryIngestPipeline._safe_str(record.get("country"), 100),
            "longitude": BreweryIngestPipeline._safe_float(record.get("longitude")),
            "latitude": BreweryIngestPipeline._safe_float(record.get("latitude")),
            "phone": BreweryIngestPipeline._safe_str(record.get("phone"), 50),
            "website_url": BreweryIngestPipeline._safe_str(record.get("website_url"), 500),
            "state": BreweryIngestPipeline._safe_str(record.get("state"), 100),
            "street": BreweryIngestPipeline._safe_str(record.get("street"), 255),
        }

    @staticmethod
    def _safe_str(value: Any, max_len: int) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return text[:max_len]

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


# Orchestrator entry points — referenced by config/orchestration/*.yml (domain_module).
def run_landing(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryIngestPipeline().run_landing(
        load_dt=kwargs.get("load_dt"),
        fixture_path=kwargs.get("fixture_path"),
    )


def run_bronze(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryIngestPipeline().run_bronze(
        load_dt=kwargs.get("load_dt"),
        landing_rows=kwargs.get("landing_rows"),
    )


def run_silver(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryIngestPipeline().run_silver(
        load_dt=kwargs.get("load_dt"),
        bronze_rows=kwargs.get("bronze_rows"),
    )


def run_ingest_pipeline(**kwargs: Any) -> dict[str, Any]:
    return BreweryIngestPipeline().run_ingest_pipeline(
        fixture_path=kwargs.get("fixture_path"),
        load_dt=kwargs.get("load_dt"),
    )

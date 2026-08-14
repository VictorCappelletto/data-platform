"""Orders ingestion — legacy wrapper; prefer workflows.runs.olist_demo."""

from __future__ import annotations

import logging
from typing import Any

from ingestion.base import IngestionBase

logger = logging.getLogger(__name__)


class OrdersIngestPipeline(IngestionBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("orders", environment)

    def to_bronze(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bronze: list[dict[str, Any]] = []
        for row in rows:
            bronze.append(
                {
                    "order_id": str(row["order_id"]).strip(),
                    "customer_id": str(row["customer_id"]).strip(),
                    "order_status": str(row["order_status"]).strip().lower(),
                    "order_purchase_timestamp": str(row["order_purchase_timestamp"]),
                    "order_approved_at": str(row["order_approved_at"])
                    if row.get("order_approved_at")
                    else None,
                    "order_delivered_carrier_date": str(row["order_delivered_carrier_date"])
                    if row.get("order_delivered_carrier_date")
                    else None,
                    "order_delivered_customer_date": str(row["order_delivered_customer_date"])
                    if row.get("order_delivered_customer_date")
                    else None,
                    "order_estimated_delivery_date": str(row["order_estimated_delivery_date"])
                    if row.get("order_estimated_delivery_date")
                    else None,
                }
            )
        return bronze


def run_landing(**_kwargs: Any) -> str:
    logger.warning("ingestion.orders.run_landing is legacy; use orchestrator.extraction.run_landing_export")
    from ingestion.landing_export import run_landing_export

    counts = run_landing_export()
    return f"orders:{counts.get('orders', 0)} rows"


def run_pipeline(**_kwargs: Any) -> dict[str, Any]:
    logger.warning("ingestion.orders.run_pipeline is legacy; use workflows.runs.olist_demo.run_full")
    from workflows.runs.olist_demo import run_full

    return run_full(**_kwargs)

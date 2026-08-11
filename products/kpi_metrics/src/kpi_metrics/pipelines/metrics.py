from __future__ import annotations

from typing import Any

from platform_dbutils import LakeIO, Layer, LayerPaths
from platform_utils.logging import get_logger

logger = get_logger(__name__)


def compute_kpis(silver_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate simple KPIs from current silver orders (synthetic demo)."""
    current = [r for r in silver_rows if r.get("is_current")]
    completed = [r for r in current if r.get("status") == "completed"]
    total_amount = sum(float(r["amount"]) for r in completed)
    unique_customers = len({r["customer_id"] for r in current})
    completion_rate = (len(completed) / len(current)) if current else 0.0
    return [
        {
            "kpi_name": "gmv_completed",
            "kpi_value": round(total_amount, 2),
            "country": "BR",
            "grain": "daily_demo",
        },
        {
            "kpi_name": "active_customers",
            "kpi_value": float(unique_customers),
            "country": "BR",
            "grain": "daily_demo",
        },
        {
            "kpi_name": "completion_rate",
            "kpi_value": round(completion_rate, 4),
            "country": "BR",
            "grain": "daily_demo",
        },
    ]


def run_kpi_pipeline() -> list[dict[str, Any]]:
    paths = LayerPaths()
    io = LakeIO(paths)
    silver = io.read_json(paths.table_path(Layer.SILVER, "orders", "orders"))
    kpis = compute_kpis(silver)
    dest = paths.table_path(Layer.GOLD, "kpi", "orders_daily")
    io.write_json(dest, kpis)
    logger.info("gold KPIs written: %s metrics", len(kpis))
    return kpis

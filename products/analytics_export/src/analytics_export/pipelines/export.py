from __future__ import annotations

from typing import Any

from platform_dbutils import LakeIO, Layer, LayerPaths
from platform_dq import null_rate, range_check, run_checks, volume_vs_baseline
from platform_utils.logging import get_logger

logger = get_logger(__name__)


def run_export(*, baseline_kpi_count: int = 3) -> list[dict[str, Any]]:
    """Validate gold KPIs and export a consumption snapshot."""
    paths = LayerPaths()
    io = LakeIO(paths)
    gold = io.read_json(paths.table_path(Layer.GOLD, "kpi", "orders_daily"))

    results = [
        null_rate(gold, "kpi_name", max_rate=0.0),
        null_rate(gold, "kpi_value", max_rate=0.0),
        range_check(gold, "kpi_value", min_value=0.0),
        volume_vs_baseline(len(gold), baseline_kpi_count, max_variance_pct=0.0),
    ]
    run_checks(results)

    export_rows = [
        {
            "kpi_name": r["kpi_name"],
            "kpi_value": r["kpi_value"],
            "country": r.get("country", "BR"),
            "export_channel": "parquet_demo",
        }
        for r in gold
    ]
    dest = paths.table_path(Layer.GOLD, "analytics", "kpi_export")
    io.write_json(dest, export_rows)
    logger.info("analytics export ready: %s rows", len(export_rows))
    return export_rows

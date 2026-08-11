from __future__ import annotations

from pathlib import Path
from typing import Any

from hdl_ingest.tables.orders import OrdersTable
from platform_dbutils import LakeIO, Layer, LayerPaths
from platform_utils.logging import get_logger

logger = get_logger(__name__)
DOMAIN = "orders"
TABLE = "orders"


def _repo_root() -> Path:
    # pipelines/ingest.py -> hdl_ingest -> src -> hdl_ingest -> products -> repo
    return Path(__file__).resolve().parents[5]


def run_landing(seed_csv: str | None = None) -> str:
    """Copy synthetic seed into landing zone."""
    paths = LayerPaths()
    io = LakeIO(paths)
    seed = Path(seed_csv) if seed_csv else _repo_root() / "seeds" / "orders_raw.csv"
    rows = io.read_csv(str(seed))
    dest = paths.table_path(Layer.LANDING, DOMAIN, TABLE)
    written = io.write_csv(dest, rows)
    logger.info("landing ready: %s (%s rows)", written, len(rows))
    return written


def run_bronze(landing_path: str | None = None) -> list[dict[str, Any]]:
    paths = LayerPaths()
    io = LakeIO(paths)
    source = landing_path or paths.table_path(Layer.LANDING, DOMAIN, TABLE)
    raw = io.read_csv(source)
    table = OrdersTable()
    bronze = table.to_bronze(raw)
    dest = paths.table_path(Layer.BRONZE, DOMAIN, TABLE)
    io.write_json(dest, bronze)
    logger.info("bronze ready: %s rows", len(bronze))
    return bronze


def run_silver(bronze_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    paths = LayerPaths()
    io = LakeIO(paths)
    table = OrdersTable()
    if bronze_rows is None:
        bronze_rows = io.read_json(paths.table_path(Layer.BRONZE, DOMAIN, TABLE))
    silver = table.to_silver(bronze_rows)
    dest = paths.table_path(Layer.SILVER, DOMAIN, TABLE)
    io.write_json(dest, silver)
    current = sum(1 for r in silver if r.get("is_current"))
    logger.info("silver ready: %s rows (%s current)", len(silver), current)
    return silver


def run_pipeline(seed_csv: str | None = None) -> dict[str, int]:
    run_landing(seed_csv)
    bronze = run_bronze()
    silver = run_silver(bronze)
    return {
        "bronze_rows": len(bronze),
        "silver_rows": len(silver),
        "current_rows": sum(1 for r in silver if r.get("is_current")),
    }

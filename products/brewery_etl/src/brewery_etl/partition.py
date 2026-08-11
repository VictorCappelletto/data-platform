from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from platform_dbutils import Layer, LayerPaths
from platform_utils.dates import utc_today


def load_date(value: date | None = None) -> str:
    return (value or utc_today()).isoformat()


def partition_key(record: dict) -> tuple[str, str]:
    country = (record.get("country") or "unknown").strip().upper() or "UNKNOWN"
    state = (record.get("state") or record.get("state_province") or "unknown").strip().upper()
    state = state.replace(" ", "_") or "UNKNOWN"
    return country, state


def partition_path(
    layer: Layer | str,
    *,
    country: str,
    state: str,
    load_dt: str,
    paths: LayerPaths | None = None,
) -> str:
    """Build hive-style partition path for brewery/breweries."""
    base = LayerPaths() if paths is None else paths
    table_base = base.table_path(layer, "brewery", "breweries")
    suffix = f"country={country}/state={state}/load_date={load_dt}"
    if base.backend in {"s3", "minio"}:
        return f"{table_base}/{suffix}"
    return str((Path(table_base) / suffix).as_posix())


def list_partition_dirs(root: str) -> list[Path]:
    """Return partition directories under a layer root (local backend only)."""
    base = Path(root)
    if not base.exists():
        return []
    return [p for p in base.rglob("load_date=*") if p.is_dir()]


def read_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)

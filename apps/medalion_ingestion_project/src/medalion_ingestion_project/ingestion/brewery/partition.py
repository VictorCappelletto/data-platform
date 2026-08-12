from __future__ import annotations

from datetime import date
from pathlib import Path

from dataplatform.config.loader import ConfigLoader
from dataplatform.dbutils.paths import Layer, LayerPaths
from dataplatform.utils.dates import utc_today
from medalion_ingestion_project import PROJECT_ID


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
    if paths is None:
        loader = ConfigLoader(app=PROJECT_ID)
        platform = loader.platform()
        app = loader.app_settings()
        base = LayerPaths.from_settings(platform, app)
    else:
        base = paths
    table_base = base.table_path(layer, "brewery", "breweries")
    suffix = f"country={country}/state={state}/load_date={load_dt}"
    if base.backend in {"s3", "minio"}:
        return f"{table_base}/{suffix}"
    return str((Path(table_base) / suffix).as_posix())


def list_partition_dirs(root: str) -> list[Path]:
    base = Path(root)
    if not base.exists():
        return []
    return [p for p in base.rglob("load_date=*") if p.is_dir()]

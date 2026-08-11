"""Inspect medallion lake layout and row counts (local validation)."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from dataplatform.config.loader import ConfigLoader
from dataplatform.dbutils.paths import LayerPaths

APP = "medalion_ingestion_project"


def load_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault("DATA_PLATFORM_ROOT", str(root))
    os.environ.setdefault("DATA_PLATFORM_APP", APP)
    loader = ConfigLoader(root, app=APP)
    platform = loader.platform()
    app = loader.app_settings()
    paths = LayerPaths.from_settings(platform, app)
    lake_root = Path(platform.lake.root) / platform.environment / app.lake_prefix

    print(f"=== APP: {app.app_id} ===")
    print("=== LAKE FILES ===")
    if lake_root.exists():
        for p in sorted(lake_root.rglob("*")):
            if p.is_file():
                print(f"  {p.relative_to(lake_root)}  ({p.stat().st_size} B)")
    else:
        print("  (lake empty — run demo pipeline)")

    print("\n=== ORDERS ===")
    orders = app.orders
    seed = loader.resolve_app_path(orders.seed_path)
    seed_rows = sum(1 for _ in csv.DictReader(seed.open()))
    print(f"seed: {seed_rows} rows")

    path_map = {
        "landing": paths.table_path("landing", orders.domain, orders.table) + "/data.csv",
        "bronze": paths.table_path("bronze", orders.domain, orders.table) + "/data.json",
        "silver": paths.table_path("silver", orders.domain, orders.table) + "/data.json",
        "gold/kpi": paths.table_path("gold", "kpi", "orders_daily") + "/data.json",
        "gold/analytics": paths.table_path("gold", "analytics", "kpi_export") + "/data.json",
    }
    for label, raw_path in path_map.items():
        p = Path(raw_path)
        status = "OK" if p.exists() else "MISSING"
        extra = ""
        if p.exists() and p.suffix == ".json":
            rows = load_json(p)
            extra = f"rows={len(rows)}"
        elif p.exists():
            extra = f"rows={sum(1 for _ in csv.DictReader(p.open()))}"
        print(f"  [{status}] {label}: {p.name} {extra}")

    print("\n=== BREWERY ===")
    brewery = loader.constants()["brewery"]
    domain = brewery["domain"]
    table = brewery["table"]
    for layer in ("landing", "bronze", "silver", "gold"):
        base = Path(paths.table_path(layer, domain, table))
        parts = sorted(base.rglob("load_date=*/data.json")) if base.exists() else []
        total = sum(len(load_json(f)) for f in parts)
        print(f"  {layer}: partitions={len(parts)} total_rows={total}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

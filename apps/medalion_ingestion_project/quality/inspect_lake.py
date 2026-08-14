"""Lake inspection — layout, row counts, layer health."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from workflows.orchestrator_base import APP_ID


def _load_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _row_count(path: Path) -> int:
    if path.suffix == ".json":
        return len(_load_json(path))
    return sum(1 for _ in csv.DictReader(path.open()))


def _inspect_orders(loader, paths, app) -> dict[str, Any]:
    orders = app.orders
    seed = loader.resolve_app_path(orders.seed_path)
    seed_rows = sum(1 for _ in csv.DictReader(seed.open()))

    layers: dict[str, dict[str, Any]] = {}
    path_map = {
        "landing": paths.table_path("landing", orders.domain, orders.table) + "/data.csv",
        "bronze": paths.table_path("bronze", orders.domain, orders.table) + "/data.json",
        "silver": paths.table_path("silver", orders.domain, orders.table) + "/data.json",
        "gold/kpi": paths.table_path("gold", "kpi", "orders_daily") + "/data.json",
        "gold/analytics": paths.table_path("gold", "analytics", "kpi_export") + "/data.json",
    }
    for label, raw_path in path_map.items():
        p = Path(raw_path)
        layers[label] = {
            "path": str(p),
            "exists": p.exists(),
            "rows": _row_count(p) if p.exists() else 0,
        }

    return {"seed_rows": seed_rows, "layers": layers}


def _inspect_brewery(loader, paths) -> dict[str, Any]:
    brewery = loader.constants()["brewery"]
    domain = brewery["domain"]
    table = brewery["table"]
    layers: dict[str, dict[str, Any]] = {}
    for layer in ("landing", "bronze", "silver", "gold"):
        base = Path(paths.table_path(layer, domain, table))
        parts = sorted(base.rglob("load_date=*/data.json")) if base.exists() else []
        total = sum(len(_load_json(f)) for f in parts)
        layers[layer] = {"partitions": len(parts), "total_rows": total}
    return layers


def run_inspect_lake(**_kwargs: Any) -> dict[str, Any]:
    from dataplatform.config import ConfigLoader
    from dataplatform.lake import LayerPaths
    from utils.settings import load_app_settings

    loader = ConfigLoader(app=APP_ID)
    platform = loader.platform()
    app = load_app_settings(loader)
    paths = LayerPaths.from_settings(platform, app)
    lake_root = Path(platform.lake.root) / platform.environment / app.lake_prefix

    files: list[dict[str, Any]] = []
    if lake_root.exists():
        for p in sorted(lake_root.rglob("*")):
            if p.is_file():
                files.append(
                    {
                        "path": str(p.relative_to(lake_root)),
                        "size_bytes": p.stat().st_size,
                    }
                )

    return {
        "app_id": app.app_id,
        "lake_root": str(lake_root),
        "files": files,
        "orders": _inspect_orders(loader, paths, app),
        "brewery": _inspect_brewery(loader, paths),
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [
        f"=== APP: {report['app_id']} ===",
        "=== LAKE FILES ===",
    ]
    if report["files"]:
        for entry in report["files"]:
            lines.append(f"  {entry['path']}  ({entry['size_bytes']} B)")
    else:
        lines.append("  (lake empty — run demo pipeline)")

    lines.append("\n=== ORDERS ===")
    lines.append(f"seed: {report['orders']['seed_rows']} rows")
    for label, layer in report["orders"]["layers"].items():
        status = "OK" if layer["exists"] else "MISSING"
        extra = f"rows={layer['rows']}" if layer["exists"] else ""
        lines.append(f"  [{status}] {label}: {extra}".rstrip())

    lines.append("\n=== BREWERY ===")
    for layer, stats in report["brewery"].items():
        lines.append(
            f"  {layer}: partitions={stats['partitions']} total_rows={stats['total_rows']}"
        )

    return "\n".join(lines)


def main() -> int:
    report = run_inspect_lake()
    print(format_report(report))
    return 0


if __name__ == "__main__":
    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID

    bootstrap(APP_ID)
    raise SystemExit(main())

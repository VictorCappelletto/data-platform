from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from platform_dbutils import LakeIO, Layer, LayerPaths
from platform_dq import CheckResult, null_rate, run_checks
from platform_utils.logging import get_logger

from brewery_etl.extract import extract_breweries, extract_from_fixture
from brewery_etl.partition import load_date, partition_key, partition_path
from brewery_etl.transform import transform_breweries

logger = get_logger(__name__)
MIN_VOLUME = 1


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _group_by_partition(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[partition_key(row)].append(row)
    return groups


def _write_partitions(
    rows: list[dict[str, Any]],
    layer: Layer,
    load_dt: str,
    *,
    paths: LayerPaths | None = None,
    io: LakeIO | None = None,
) -> int:
    lake_paths = paths or LayerPaths()
    lake_io = io or LakeIO(lake_paths)
    groups = _group_by_partition(rows)
    written = 0
    for (country, state), part_rows in groups.items():
        dest = partition_path(
            layer,
            country=country,
            state=state,
            load_dt=load_dt,
            paths=lake_paths,
        )
        lake_io.write_json(dest, part_rows)
        written += len(part_rows)
    return written


def duplicate_ids(rows: list[dict[str, Any]], column: str = "id") -> CheckResult:
    ids = [r.get(column) for r in rows if r.get(column)]
    dupes = len(ids) - len(set(ids))
    ok = dupes == 0
    return CheckResult(
        name=f"duplicate:{column}",
        passed=ok,
        message=f"duplicate_count={dupes}",
        metrics={"rows": len(rows), "duplicates": dupes},
    )


def run_landing(
    *,
    load_dt: str | None = None,
    fixture_path: str | None = None,
) -> list[dict[str, Any]]:
    load_dt = load_dt or load_date()
    if fixture_path:
        raw = extract_from_fixture(fixture_path)
    elif os.getenv("BREWERY_USE_FIXTURE", "0") == "1":
        raw = extract_from_fixture(str(_repo_root() / "seeds" / "breweries_sample.json"))
    else:
        raw = extract_breweries()
    _write_partitions(raw, Layer.LANDING, load_dt)
    logger.info("landing complete: %s rows load_date=%s", len(raw), load_dt)
    return raw


def run_bronze(
    *,
    load_dt: str | None = None,
    landing_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    load_dt = load_dt or load_date()
    if landing_rows is None:
        landing_rows = _read_layer_partitions(Layer.LANDING, load_dt)
    bronze = transform_breweries(landing_rows)
    _write_partitions(bronze, Layer.BRONZE, load_dt)
    logger.info("bronze complete: %s rows", len(bronze))
    return bronze


def run_silver(
    *,
    load_dt: str | None = None,
    bronze_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    load_dt = load_dt or load_date()
    if bronze_rows is None:
        bronze_rows = _read_layer_partitions(Layer.BRONZE, load_dt)
    silver = _dedupe_by_id(bronze_rows)
    _write_partitions(silver, Layer.SILVER, load_dt)
    logger.info("silver complete: %s rows (deduped)", len(silver))
    return silver


def _read_layer_partitions(layer: Layer, load_dt: str) -> list[dict[str, Any]]:
    paths = LayerPaths()
    base = paths.table_path(layer, "brewery", "breweries")
    if paths.backend in {"s3", "minio"}:
        raise NotImplementedError("partition read for s3 backend not implemented in v1")
    root = Path(base)
    rows: list[dict[str, Any]] = []
    for file_path in root.glob(f"**/load_date={load_dt}/data.json"):
        rows.extend(LakeIO(paths).read_json(str(file_path)))
    return rows


def _dedupe_by_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get("id")
        if key:
            by_id[key] = row
    return list(by_id.values())


def check_min_volume(rows: list[dict[str, Any]], minimum: int = MIN_VOLUME) -> CheckResult:
    count = len(rows)
    ok = count >= minimum
    return CheckResult(
        name="min_volume",
        passed=ok,
        message=f"count={count} min={minimum}",
        metrics={"count": count, "minimum": minimum},
    )


def run_dq_gold(
    *,
    load_dt: str | None = None,
    min_volume: int = MIN_VOLUME,
) -> list[dict[str, Any]]:
    load_dt = load_dt or load_date()
    silver = _read_layer_partitions(Layer.SILVER, load_dt)
    results = [
        null_rate(silver, "id", max_rate=0.0),
        null_rate(silver, "name", max_rate=0.0),
        null_rate(silver, "brewery_type", max_rate=0.0),
        duplicate_ids(silver, "id"),
        check_min_volume(silver, min_volume),
    ]
    run_checks(results)

    gold = silver  # v1: gold mirrors validated silver by state partition
    _write_partitions(gold, Layer.GOLD, load_dt)
    logger.info("gold complete: %s rows after DQ", len(gold))
    return gold


def run_ingest_pipeline(
    *,
    fixture_path: str | None = None,
    load_dt: str | None = None,
) -> dict[str, Any]:
    load_dt = load_dt or load_date()
    landing = run_landing(load_dt=load_dt, fixture_path=fixture_path)
    bronze = run_bronze(load_dt=load_dt, landing_rows=landing)
    silver = run_silver(load_dt=load_dt, bronze_rows=bronze)
    return {
        "landing_rows": len(landing),
        "bronze_rows": len(bronze),
        "silver_rows": len(silver),
        "load_date": load_dt,
    }


def run_full_pipeline(
    *,
    fixture_path: str | None = None,
    load_dt: str | None = None,
) -> dict[str, Any]:
    stats = run_ingest_pipeline(fixture_path=fixture_path, load_dt=load_dt)
    gold = run_dq_gold(load_dt=stats["load_date"])
    stats["gold_rows"] = len(gold)
    return stats

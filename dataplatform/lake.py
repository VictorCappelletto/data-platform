"""Lake paths, local IO, and optional Spark session."""

from __future__ import annotations

import csv
import json
import os
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dataplatform.paths import ensure_dir, ensure_write_parent
from dataplatform.utils import get_logger

if TYPE_CHECKING:
    from dataplatform.config import AppSettings, PlatformSettings

logger = get_logger(__name__)


class Layer(str, Enum):
    LANDING = "landing"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class LayerPaths:
    def __init__(
        self,
        *,
        env: str,
        root: str,
        backend: str,
        bucket: str,
        lake_prefix: str = "",
    ) -> None:
        self.env = env.lower()
        self.backend = backend.lower()
        self.root = root
        self.bucket = bucket
        self.lake_prefix = lake_prefix.strip("/")

    @classmethod
    def from_settings(
        cls,
        settings: PlatformSettings,
        project: AppSettings | None = None,
    ) -> LayerPaths:
        return cls(
            env=settings.environment,
            root=settings.lake.root,
            backend=settings.lake.backend,
            bucket=settings.lake.bucket,
            lake_prefix=project.lake_prefix if project else "",
        )

    def table_path(self, layer: Layer | str, domain: str, table: str) -> str:
        layer_name = layer.value if isinstance(layer, Layer) else layer
        parts = [layer_name, domain, table]
        if self.lake_prefix:
            parts.insert(0, self.lake_prefix)
        relative = "/".join(parts)
        if self.backend in {"s3", "minio"}:
            return f"s3a://{self.bucket}/{self.env}/{relative}"
        path = Path(self.root) / self.env / relative
        return str(path.as_posix())

    def ensure_local(self, path: str) -> Path:
        return ensure_dir(path)


class LakeIO:
    def __init__(self, paths: LayerPaths | None = None) -> None:
        if paths is None:
            from dataplatform.config import ConfigLoader

            paths = LayerPaths.from_settings(ConfigLoader().platform())
        self.paths = paths

    def write_json(self, path: str, rows: list[dict[str, Any]]) -> str:
        target = Path(path)
        if target.suffix:
            ensure_write_parent(target)
            file_path = target
        else:
            ensure_dir(path)
            file_path = Path(path) / "data.json"
        with file_path.open("w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2, default=str)
        logger.info("wrote %s rows -> %s", len(rows), file_path)
        return str(file_path)

    def read_json(self, path: str) -> list[dict[str, Any]]:
        file_path = Path(path)
        if file_path.is_dir():
            file_path = file_path / "data.json"
        with file_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError(f"Expected list JSON at {file_path}")
        return data

    def write_csv(self, path: str, rows: list[dict[str, Any]]) -> str:
        if not rows:
            raise ValueError("Cannot write empty CSV")
        target = Path(path)
        if target.suffix:
            ensure_write_parent(target)
            file_path = target
        else:
            ensure_dir(path)
            file_path = Path(path) / "data.csv"
        with file_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        logger.info("wrote %s rows -> %s", len(rows), file_path)
        return str(file_path)

    def read_csv(self, path: str) -> list[dict[str, Any]]:
        file_path = Path(path)
        if file_path.is_dir():
            file_path = file_path / "data.csv"
        with file_path.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))


def get_spark(app_name: str = "data-platform", **kwargs: Any):
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "pyspark is not installed. pip install 'data-platform[spark]'"
        ) from exc

    if os.name == "nt":
        try:
            from transformation.io import spark_hadoop_configs

            kwargs = {**spark_hadoop_configs(), **kwargs}
        except ImportError:
            pass

    builder = (
        SparkSession.builder.appName(app_name)
        .master(os.getenv("SPARK_MASTER", "local[*]"))
        .config("spark.sql.shuffle.partitions", kwargs.get("shuffle_partitions", "4"))
    )

    if os.getenv("ENABLE_DELTA", "0") == "1":
        builder = (
            builder.config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config(
                "spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog",
            )
        )

    for key, value in kwargs.items():
        if key.startswith("spark."):
            builder = builder.config(key, value)

    return builder.getOrCreate()

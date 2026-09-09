"""Shared base for transformation process — engine dispatch + notebook steps."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Literal

from dataplatform.process_base import ProjectProcessBase
from transformation.io import OlistLakeMount, ensure_spark_friendly_lake_root, ensure_winutils_chmod
from utils.settings import bind_azure_settings


class TransformationBase(ProjectProcessBase, ABC):
    def __init__(self, domain_key: str = "olist", environment: str | None = None) -> None:
        super().__init__("transformation", domain_key, environment)
        bind_azure_settings(self, environment)
        self.mount = OlistLakeMount(
            lake_prefix=self.app.lake_prefix,
            environment=self.platform.environment,
        )
        self._spark = None

    @property
    def engine(self) -> Literal["local", "spark"]:
        """Resolve engine from OLIST_PROCESSING_ENGINE env, then config YAML."""
        raw = os.getenv("OLIST_PROCESSING_ENGINE")
        if not raw:
            raw = self.product_config.get("processing", {}).get("engine")
        value = (raw or "local").strip().lower()
        if value not in {"local", "spark"}:
            raise ValueError(f"Invalid processing engine: {value!r} (use local or spark)")
        return value  # type: ignore[return-value]

    @property
    def tables(self) -> list[str]:
        return list(self.product_config.get("tables", []))

    @property
    def database(self) -> str:
        return self.product_config.get("database", "customers_db")

    def spark_session(self, app_name: str):
        if self._spark is None:
            from dataplatform.lake import get_spark

            staging = ensure_spark_friendly_lake_root(os.getenv("LAKE_ROOT", "./data/lake"))
            ensure_winutils_chmod(staging)
            backend = os.getenv("OLIST_LAKE_BACKEND", "local")
            self.mount = OlistLakeMount(
                lake_root=staging,
                lake_prefix=self.app.lake_prefix,
                environment=self.platform.environment,
                backend=backend,
                storage_account=os.getenv("AZURE_STORAGE_ACCOUNT", ""),
            )
            self._spark = get_spark(app_name)
        return self._spark

    def log_mount(self) -> dict[str, str]:
        zones = {zone: self.mount.zone_uri(zone) for zone in self.mount.zones}
        self.logger.info("mount points (%s): %s", self.engine, zones)
        return zones

    @abstractmethod
    def landing_frames_local(self) -> dict[str, list[dict[str, Any]]]:
        """Read landing CSVs as in-memory rows (pyarrow path)."""

    @abstractmethod
    def landing_frames_spark(self) -> dict[str, Any]:
        """Read landing CSVs as Spark DataFrames."""

    def read_landing(self) -> dict[str, int]:
        if self.engine == "spark":
            return {name: df.count() for name, df in self.landing_frames_spark().items()}
        return {name: len(rows) for name, rows in self.landing_frames_local().items()}

    @abstractmethod
    def write_processing_local(self, frames: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
        """Write full-table parquet under processing/."""

    @abstractmethod
    def write_processing_spark(self, frames: dict[str, Any]) -> dict[str, str]:
        """Write full-table parquet under processing/ (Spark)."""

    def write_processing(self) -> dict[str, str]:
        if self.engine == "spark":
            return self.write_processing_spark(self.landing_frames_spark())
        return self.write_processing_local(self.landing_frames_local())

    @abstractmethod
    def run_curated_local(self, frames: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """Filter + write filtered parquet and curated CSV (local)."""

    @abstractmethod
    def run_curated_spark(self, frames: dict[str, Any]) -> dict[str, Any]:
        """Filter + write filtered parquet and curated CSV (Spark)."""

    def run_curated(self) -> dict[str, Any]:
        if self.engine == "spark":
            return self.run_curated_spark(self.landing_frames_spark())
        return self.run_curated_local(self.landing_frames_local())

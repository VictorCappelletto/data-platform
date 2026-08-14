"""Olist domain — transformation pipeline and Spark SQL catalog."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from transformation.base import TransformationBase

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

logger = logging.getLogger(__name__)


class OlistTransformPipeline(TransformationBase):
    """Olist notebook steps — local/spark implementations; dispatch lives in TransformationBase."""

    def landing_frames_local(self) -> dict[str, list[dict[str, Any]]]:
        frames: dict[str, list[dict[str, Any]]] = {}
        for table in self.tables:
            path = self.mount.file_path("landing", f"{table}.csv")
            rows = self.mount.read_csv(path)
            self.logger.info("read landing %s: %s rows", table, len(rows))
            frames[table] = rows
        return frames

    def landing_frames_spark(self) -> dict[str, DataFrame]:
        spark = self.spark_session("ingestion_azure-olist")
        frames: dict[str, DataFrame] = {}
        for table in self.tables:
            path = self.mount.spark_data_path("landing", f"{table}.csv")
            df = (
                spark.read.format("csv")
                .option("header", "true")
                .option("inferSchema", "true")
                .option("delimiter", ",")
                .load(path)
            )
            self.logger.info("spark read landing %s from %s", table, path)
            frames[table] = df
        return frames

    def write_processing_local(self, frames: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
        outputs: dict[str, str] = {}
        for table, rows in frames.items():
            path = self.mount.file_path("processing", f"{table}.parquet")
            outputs[table] = self.mount.write_parquet(path, rows)
            self.logger.info("processing parquet %s: %s rows", table, len(rows))
        return outputs

    def write_processing_spark(self, frames: dict[str, DataFrame]) -> dict[str, str]:
        outputs: dict[str, str] = {}
        for table, df in frames.items():
            path = self.mount.spark_data_path("processing", f"{table}.parquet")
            df.write.mode("overwrite").parquet(path)
            self.logger.info("spark processing parquet %s -> %s", table, path)
            outputs[table] = path
        return outputs

    def _apply_filters_local(
        self, frames: dict[str, list[dict[str, Any]]]
    ) -> dict[str, list[dict[str, Any]]]:
        filtered: dict[str, list[dict[str, Any]]] = {}
        for table, rules in self.product_config.get("filters", {}).items():
            if table not in frames:
                self.logger.warning("filter skipped — %s not in landing frames", table)
                continue
            for rule in rules:
                output = rule["output"]
                column = rule["column"]
                target = str(rule["value"]).strip()
                filtered[output] = [
                    row for row in frames[table] if str(row.get(column, "")).strip() == target
                ]
                self.logger.info(
                    "filter %s.%s=%s -> %s (%s rows)",
                    table,
                    column,
                    target,
                    output,
                    len(filtered[output]),
                )
        return filtered

    def _apply_filters_spark(self, frames: dict[str, DataFrame]) -> dict[str, DataFrame]:
        from pyspark.sql.functions import col

        filtered: dict[str, DataFrame] = {}
        for table, rules in self.product_config.get("filters", {}).items():
            if table not in frames:
                self.logger.warning("filter skipped — %s not in landing frames", table)
                continue
            for rule in rules:
                output = rule["output"]
                column = rule["column"]
                value = str(rule["value"])
                filtered[output] = frames[table].filter(col(column) == value)
                self.logger.info(
                    "spark filter %s.%s=%s -> %s (%s rows)",
                    table,
                    column,
                    value,
                    output,
                    filtered[output].count(),
                )
        return filtered

    def run_curated_local(self, frames: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        filtered = self._apply_filters_local(frames)
        processing_out = {
            name: self.mount.write_parquet(
                self.mount.file_path("processing", f"{name}.parquet"), rows
            )
            for name, rows in filtered.items()
        }
        curated_out = {
            name: self.mount.write_csv(self.mount.file_path("curated", f"{name}.csv"), rows)
            for name, rows in filtered.items()
        }
        for name, rows in filtered.items():
            self.logger.info("curated csv %s: %s rows", name, len(rows))
        return {
            "processing_parquet": processing_out,
            "curated_csv": curated_out,
            "row_counts": {name: len(rows) for name, rows in filtered.items()},
        }

    def run_curated_spark(self, frames: dict[str, DataFrame]) -> dict[str, Any]:
        filtered = self._apply_filters_spark(frames)
        processing_out: dict[str, str] = {}
        curated_out: dict[str, str] = {}
        row_counts: dict[str, int] = {}
        for name, df in filtered.items():
            processing_out[name] = self.mount.spark_data_path("processing", f"{name}.parquet")
            df.write.mode("overwrite").parquet(processing_out[name])
            curated_out[name] = self.mount.spark_data_path("curated", f"{name}.csv")
            df.write.option("header", True).option("delimiter", ",").mode("overwrite").csv(
                curated_out[name]
            )
            row_counts[name] = df.count()
            self.logger.info("spark curated %s: %s rows", name, row_counts[name])
        return {
            "processing_parquet": processing_out,
            "curated_csv": curated_out,
            "row_counts": row_counts,
        }


class SparkSqlCatalog(TransformationBase):
    """Spark-only — register customers_db external tables over lake paths."""

    def landing_frames_local(self) -> dict[str, list[dict[str, Any]]]:
        raise RuntimeError("SparkSqlCatalog requires OLIST_PROCESSING_ENGINE=spark")

    def landing_frames_spark(self) -> dict[str, DataFrame]:
        raise RuntimeError("SparkSqlCatalog uses run(), not landing reads")

    def write_processing_local(self, frames: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
        raise RuntimeError("SparkSqlCatalog requires OLIST_PROCESSING_ENGINE=spark")

    def write_processing_spark(self, frames: dict[str, DataFrame]) -> dict[str, str]:
        raise RuntimeError("SparkSqlCatalog uses run(), not write_processing")

    def run_curated_local(self, frames: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        raise RuntimeError("SparkSqlCatalog requires OLIST_PROCESSING_ENGINE=spark")

    def run_curated_spark(self, frames: dict[str, DataFrame]) -> dict[str, Any]:
        raise RuntimeError("SparkSqlCatalog uses run(), not run_curated")

    def run(self) -> dict[str, Any]:
        if self.engine != "spark":
            self.logger.warning(
                "SparkSqlCatalog skipped — engine=%s (set OLIST_PROCESSING_ENGINE=spark)",
                self.engine,
            )
            return {"engine": self.engine, "skipped": True, "database": self.database}

        spark = self.spark_session("ingestion_azure-customers_db")
        spark.sql(f"CREATE DATABASE IF NOT EXISTS {self.database}")

        processing: dict[str, str] = {}
        for table in self.tables:
            name = f"{table}_pqt"
            path = self.mount.spark_data_path("processing", f"{table}.parquet")
            qualified = f"{self.database}.{name}"
            spark.sql(f"DROP TABLE IF EXISTS {qualified}")
            spark.sql(f"CREATE TABLE {qualified} USING parquet OPTIONS (path '{path}')")
            processing[name] = path
            self.logger.info("registered %s -> %s", qualified, path)

        filtered: dict[str, str] = {}
        curated: dict[str, str] = {}
        for _table, rules in self.product_config.get("filters", {}).items():
            for rule in rules:
                output = rule["output"]
                pqt_name = f"{output}_pqt"
                pqt_path = self.mount.spark_data_path("processing", f"{output}.parquet")
                pqt_qualified = f"{self.database}.{pqt_name}"
                spark.sql(f"DROP TABLE IF EXISTS {pqt_qualified}")
                spark.sql(
                    f"CREATE TABLE {pqt_qualified} USING parquet OPTIONS (path '{pqt_path}')"
                )
                filtered[pqt_name] = pqt_path

                csv_name = f"{output}_csv"
                csv_path = self.mount.spark_data_path("curated", f"{output}.csv")
                csv_qualified = f"{self.database}.{csv_name}"
                spark.sql(f"DROP TABLE IF EXISTS {csv_qualified}")
                spark.sql(
                    f"CREATE TABLE {csv_qualified} USING csv "
                    f"OPTIONS (path '{csv_path}', header 'true', inferSchema 'true')"
                )
                curated[csv_name] = csv_path
                self.logger.info("registered %s, %s", pqt_qualified, csv_qualified)

        all_tables = list(processing) + list(filtered) + list(curated)
        row_counts = {name: spark.table(f"{self.database}.{name}").count() for name in all_tables}
        return {
            "engine": "spark",
            "database": self.database,
            "processing_parquet_tables": processing,
            "filtered_parquet_tables": filtered,
            "curated_csv_tables": curated,
            "row_counts": row_counts,
        }


def _env_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    env = kwargs.get("environment")
    return {"environment": env} if env is not None else {}


def run_mount(**kwargs: Any) -> dict[str, str]:
    return OlistTransformPipeline(**_env_kwargs(kwargs)).log_mount()


def run_read_landing(**kwargs: Any) -> dict[str, int]:
    return OlistTransformPipeline(**_env_kwargs(kwargs)).read_landing()


def run_write_processing(**kwargs: Any) -> dict[str, str]:
    return OlistTransformPipeline(**_env_kwargs(kwargs)).write_processing()


def run_curated(**kwargs: Any) -> dict[str, Any]:
    return OlistTransformPipeline(**_env_kwargs(kwargs)).run_curated()


def run_sql_catalog(**kwargs: Any) -> dict[str, Any]:
    return SparkSqlCatalog(**_env_kwargs(kwargs)).run()


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    logger.warning(
        "transformation.olist.run_pipeline is legacy; "
        "use workflows.runs.olist_demo --mode full"
    )
    from workflows.runs.olist_demo import run_full

    return run_full(**kwargs)


def run_pipeline_from_landing(**kwargs: Any) -> dict[str, Any]:
    logger.warning(
        "transformation.olist.run_pipeline_from_landing is legacy; "
        "use workflows.runs.olist_demo --mode transform_from_landing"
    )
    from workflows.runs.olist_demo import run_transform_from_landing

    return run_transform_from_landing(**kwargs)

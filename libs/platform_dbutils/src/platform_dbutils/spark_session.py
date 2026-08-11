from __future__ import annotations

import os
from typing import Any


def get_spark(app_name: str = "data-platform", **kwargs: Any):
    """
    Create a SparkSession when pyspark is installed.

    Local default uses master=local[*]. For Delta, set ENABLE_DELTA=1.
    """
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "pyspark is not installed. pip install 'data-platform[spark]' or platform-dbutils[spark]"
        ) from exc

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

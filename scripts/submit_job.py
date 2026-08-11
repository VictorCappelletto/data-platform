"""Optional spark-submit style entrypoint (requires pyspark)."""

from __future__ import annotations

import argparse

from platform_dbutils import get_spark
from platform_utils.logging import get_logger

logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke Spark session for data-platform")
    parser.add_argument("--app-name", default="data-platform-smoke")
    args = parser.parse_args()
    spark = get_spark(args.app_name)
    logger.info("Spark version=%s", spark.version)
    spark.range(0, 5).show()
    spark.stop()


if __name__ == "__main__":
    main()

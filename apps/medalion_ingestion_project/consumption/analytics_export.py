"""Analytics export — gold KPIs → export layer with DQ gate."""

from __future__ import annotations

from typing import Any

from consumption.base import ConsumptionBase
from dataplatform.data_quality import run_checks
from dataplatform.lake import Layer


class AnalyticsExportPipeline(ConsumptionBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("analytics_export", environment)

    def transform(self, gold_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kpi_cfg = self.constants["kpi"]
        return [
            {
                "kpi_name": row["kpi_name"],
                "kpi_value": row["kpi_value"],
                "country": row.get("country", self.constants["countries"]["default"]),
                "export_channel": kpi_cfg["export_channel"],
            }
            for row in gold_rows
        ]

    def run(self) -> list[dict[str, Any]]:
        source = self.product_config["source"]
        target = self.product_config["target"]
        gold = self.io.read_json(
            self.paths.table_path(Layer(source["layer"]), source["domain"], source["table"])
        )
        dq_cfg = self.product_config["dq"]
        kpi_cfg = self.constants["kpi"]
        from dataplatform.data_quality import null_rate, range_check, volume_vs_baseline

        results = [null_rate(gold, col, max_rate=0.0) for col in dq_cfg["null_columns"]]
        results.append(range_check(gold, "kpi_value", min_value=dq_cfg["min_value"]))
        results.append(
            volume_vs_baseline(len(gold), kpi_cfg["baseline_count"], max_variance_pct=kpi_cfg["max_variance_pct"])
        )
        run_checks(results)
        export_rows = self.transform(gold)
        dest = self.paths.table_path(Layer(target["layer"]), target["domain"], target["table"])
        self.io.write_json(dest, export_rows)
        self.logger.info("analytics export ready: %s rows", len(export_rows))
        return export_rows


def run_export(**_kwargs: Any) -> list[dict[str, Any]]:
    return AnalyticsExportPipeline().run()

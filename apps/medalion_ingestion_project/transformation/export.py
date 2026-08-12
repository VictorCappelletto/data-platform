"""Analytics export — gold KPIs → export layer with DQ gate."""

from __future__ import annotations

from typing import Any

from transformation.base import TransformationBase


class AnalyticsExportPipeline(TransformationBase):
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

    def run_export(self) -> list[dict[str, Any]]:
        gold = self.read_source_rows()
        dq_cfg = self.product_config["dq"]
        kpi_cfg = self.constants["kpi"]
        self.run_standard_export_dq(
            gold,
            null_columns=dq_cfg["null_columns"],
            min_value=dq_cfg["min_value"],
            baseline_count=kpi_cfg["baseline_count"],
            max_variance_pct=kpi_cfg["max_variance_pct"],
        )
        export_rows = self.transform(gold)
        self.write_target_rows(export_rows)
        self.logger.info("analytics export ready: %s rows", len(export_rows))
        return export_rows


# Orchestrator entry point — referenced by config/orchestration/*.yml (domain_module).
def run_export(**_kwargs: Any) -> list[dict[str, Any]]:
    return AnalyticsExportPipeline().run_export()

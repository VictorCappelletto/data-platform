from __future__ import annotations

from typing import Any

from dataplatform.dbutils.paths import Layer
from dataplatform.dq import null_rate, range_check, run_checks, volume_vs_baseline
from medalion_ingestion_project.base import ProjectProductBase


class AnalyticsExportPipeline(ProjectProductBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("analytics_export", environment)

    def run_export(self) -> list[dict[str, Any]]:
        source = self.product_config["source"]
        target = self.product_config["target"]
        dq_cfg = self.product_config["dq"]
        kpi_cfg = self.constants["kpi"]

        gold = self.io.read_json(
            self.paths.table_path(Layer.GOLD, source["domain"], source["table"])
        )

        results = [
            null_rate(gold, col, max_rate=0.0) for col in dq_cfg["null_columns"]
        ]
        results.append(range_check(gold, "kpi_value", min_value=dq_cfg["min_value"]))
        results.append(
            volume_vs_baseline(
                len(gold),
                kpi_cfg["baseline_count"],
                max_variance_pct=kpi_cfg["max_variance_pct"],
            )
        )
        run_checks(results)

        export_rows = [
            {
                "kpi_name": r["kpi_name"],
                "kpi_value": r["kpi_value"],
                "country": r.get("country", self.constants["countries"]["default"]),
                "export_channel": kpi_cfg["export_channel"],
            }
            for r in gold
        ]
        dest = self.paths.table_path(Layer.GOLD, target["domain"], target["table"])
        self.io.write_json(dest, export_rows)
        self.logger.info("analytics export ready: %s rows", len(export_rows))
        return export_rows


def run_export(**_kwargs: Any) -> list[dict[str, Any]]:
    return AnalyticsExportPipeline().run_export()

from __future__ import annotations

from typing import Any

from dataplatform.dbutils.paths import Layer
from medalion_ingestion_project.base import ProjectProductBase


class KpiMetricsPipeline(ProjectProductBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("kpi_metrics", environment)

    def compute_kpis(self, silver_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        country = self.constants["countries"]["default"]
        grain = self.constants["kpi"]["grain"]
        current = [r for r in silver_rows if r.get("is_current")]
        completed = [r for r in current if r.get("status") == "completed"]
        total_amount = sum(float(r["amount"]) for r in completed)
        unique_customers = len({r["customer_id"] for r in current})
        completion_rate = (len(completed) / len(current)) if current else 0.0
        return [
            {
                "kpi_name": "gmv_completed",
                "kpi_value": round(total_amount, 2),
                "country": country,
                "grain": grain,
            },
            {
                "kpi_name": "active_customers",
                "kpi_value": float(unique_customers),
                "country": country,
                "grain": grain,
            },
            {
                "kpi_name": "completion_rate",
                "kpi_value": round(completion_rate, 4),
                "country": country,
                "grain": grain,
            },
        ]

    def run_kpi_pipeline(self) -> list[dict[str, Any]]:
        source = self.product_config["source"]
        target = self.product_config["target"]
        silver = self.io.read_json(
            self.paths.table_path(Layer.SILVER, source["domain"], source["table"])
        )
        kpis = self.compute_kpis(silver)
        dest = self.paths.table_path(Layer.GOLD, target["domain"], target["table"])
        self.io.write_json(dest, kpis)
        self.logger.info("gold KPIs written: %s metrics", len(kpis))
        return kpis


def compute_kpis(silver_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return KpiMetricsPipeline().compute_kpis(silver_rows)


def run_kpi_pipeline(**_kwargs: Any) -> list[dict[str, Any]]:
    return KpiMetricsPipeline().run_kpi_pipeline()

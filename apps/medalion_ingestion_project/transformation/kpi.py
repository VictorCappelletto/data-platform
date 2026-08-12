"""KPI transformation — silver orders → gold KPI metrics."""

from __future__ import annotations

from typing import Any

from transformation.base import TransformationBase


class KpiTransformPipeline(TransformationBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("kpi", environment)

    def transform(self, silver_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        return self.run()


# Orchestrator entry point — referenced by config/orchestration/*.yml (domain_module).
def run_kpi_pipeline(**_kwargs: Any) -> list[dict[str, Any]]:
    return KpiTransformPipeline().run_kpi_pipeline()

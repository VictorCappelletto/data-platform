"""Project-scoped ProductBase with project id baked in."""

from __future__ import annotations

from dataplatform.products.base import ProductBase
from medalion_ingestion_project import PROJECT_ID


class ProjectProductBase(ProductBase):
    def __init__(self, product_name: str, environment: str | None = None) -> None:
        super().__init__(product_name, environment, project=PROJECT_ID)

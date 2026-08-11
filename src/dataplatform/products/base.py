"""Shared base for app product pipelines."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dataplatform.config.loader import AppSettings, ConfigLoader, PlatformSettings
from dataplatform.dbutils.io import LakeIO
from dataplatform.dbutils.paths import LayerPaths
from dataplatform.utils.logging import get_logger


def _default_app_id() -> str:
    return os.getenv("DATA_PLATFORM_APP") or os.getenv("DATA_PLATFORM_PROJECT", "")


class ProductBase:
    """Inject platform + app + product YAML config into pipelines."""

    def __init__(
        self,
        product_name: str,
        environment: str | None = None,
        app: str | None = None,
        project: str | None = None,
    ) -> None:
        self.product_name = product_name
        self.app_id = app or project or _default_app_id()
        if not self.app_id:
            raise ValueError("DATA_PLATFORM_APP must be set for product pipelines")
        self.loader = ConfigLoader(app=self.app_id)
        self.platform: PlatformSettings = self.loader.platform(environment)
        self.app: AppSettings = self.loader.app_settings(environment)
        self.project = self.app  # backward-compatible alias
        self.product_config: dict[str, Any] = self.loader.product(product_name)
        self.constants: dict[str, Any] = self.loader.constants()
        self.paths = LayerPaths.from_settings(self.platform, self.app)
        self.io = LakeIO(self.paths)
        self.logger = get_logger(self.__class__.__name__)

    @property
    def project_id(self) -> str:
        return self.app_id

    @property
    def repo_root(self) -> Path:
        return self.loader.root

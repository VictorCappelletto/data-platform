"""Shared base for app process classes (config/<process>/config_<process>.yml)."""

from __future__ import annotations

from pathlib import Path

from dataplatform.config import ConfigLoader
from dataplatform.lake import LakeIO, LayerPaths
from dataplatform.utils import get_logger


class ProjectProcessBase:
    def __init__(self, process: str, domain_key: str, environment: str | None = None) -> None:
        loader = ConfigLoader()
        if not loader.app:
            raise ValueError(
                "DATA_PLATFORM_APP required — call dataplatform.bootstrap.bootstrap() first"
            )
        self.process_name = process
        self.domain_key = domain_key
        self.product_name = f"{process}:{domain_key}"
        self.app_id = loader.app
        self.loader = loader
        self.platform = loader.platform(environment)
        generic_app = loader.app_settings(environment)
        self.app = generic_app
        self.project = generic_app
        process_cfg = loader.process(process, environment)
        domain_cfg = process_cfg.get(domain_key)
        if domain_cfg is None:
            raise KeyError(f"Domain '{domain_key}' not found in process '{process}' config")
        self.product_config = domain_cfg
        self.constants = loader.constants()
        self.paths = LayerPaths.from_settings(self.platform, generic_app)
        self.io = LakeIO(self.paths)
        self.logger = get_logger(self.__class__.__name__)

    @property
    def project_id(self) -> str:
        return self.app_id

    @property
    def repo_root(self) -> Path:
        return self.loader.root

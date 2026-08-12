"""Project-scoped pipeline base with process-oriented config."""

from __future__ import annotations

from pathlib import Path

from dataplatform.config import ConfigLoader
from dataplatform.lake import LakeIO, LayerPaths
from dataplatform.utils import get_logger
from runtime import APP_ID
from utils.settings import load_app_settings


class ProjectProcessBase:
    """Load domain config from config/<process>/config_<process>.yml."""

    def __init__(self, process: str, domain_key: str, environment: str | None = None) -> None:
        self.process_name = process
        self.domain_key = domain_key
        self.product_name = f"{process}:{domain_key}"
        self.app_id = APP_ID
        self.loader = ConfigLoader(app=APP_ID)
        self.platform = self.loader.platform(environment)
        self.app = load_app_settings(self.loader, environment)
        self.project = self.app
        process_cfg = self.loader.process(process, environment)
        domain_cfg = process_cfg.get(domain_key)
        if domain_cfg is None:
            raise KeyError(f"Domain '{domain_key}' not found in process '{process}' config")
        self.product_config = domain_cfg
        self.constants = self.loader.constants()
        self.paths = LayerPaths.from_settings(self.platform, self.app)
        self.io = LakeIO(self.paths)
        self.logger = get_logger(self.__class__.__name__)

    @property
    def project_id(self) -> str:
        return self.app_id

    @property
    def repo_root(self) -> Path:
        return self.loader.root

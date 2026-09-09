"""Shared base for consumption layer (exports, publish)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from dataplatform.process_base import ProjectProcessBase
from utils.settings import bind_medalion_settings


class ConsumptionBase(ProjectProcessBase, ABC):
    def __init__(self, domain_key: str, environment: str | None = None) -> None:
        super().__init__("consumption", domain_key, environment)
        bind_medalion_settings(self, environment)

    @abstractmethod
    def run(self) -> Any:
        """Publish or export consumption-ready datasets."""

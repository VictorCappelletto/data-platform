from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LakeTable(ABC):
    """Base contract for entity-specific transformations (portfolio pattern)."""

    domain: str = "demo"
    table: str = "entity"

    @abstractmethod
    def to_bronze(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def to_silver(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError

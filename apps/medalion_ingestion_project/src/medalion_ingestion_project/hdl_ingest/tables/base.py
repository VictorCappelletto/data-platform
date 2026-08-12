from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LakeTable(ABC):
    """Base contract for entity-specific transformations."""

    domain: str
    table: str

    @abstractmethod
    def to_bronze(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def to_silver(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError

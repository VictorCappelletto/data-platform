from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataplatform.config.loader import PlatformSettings, ProjectSettings


class Layer(str, Enum):
    LANDING = "landing"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class LayerPaths:
    """Environment-aware lake path builder."""

    def __init__(
        self,
        *,
        env: str,
        root: str,
        backend: str,
        bucket: str,
        lake_prefix: str = "",
    ) -> None:
        self.env = env.lower()
        self.backend = backend.lower()
        self.root = root
        self.bucket = bucket
        self.lake_prefix = lake_prefix.strip("/")

    @classmethod
    def from_settings(
        cls,
        settings: PlatformSettings,
        project: ProjectSettings | None = None,
    ) -> LayerPaths:
        return cls(
            env=settings.environment,
            root=settings.lake.root,
            backend=settings.lake.backend,
            bucket=settings.lake.bucket,
            lake_prefix=project.lake_prefix if project else "",
        )

    def table_path(self, layer: Layer | str, domain: str, table: str) -> str:
        layer_name = layer.value if isinstance(layer, Layer) else layer
        parts = [layer_name, domain, table]
        if self.lake_prefix:
            parts.insert(0, self.lake_prefix)
        relative = "/".join(parts)
        if self.backend in {"s3", "minio"}:
            return f"s3a://{self.bucket}/{self.env}/{relative}"
        path = Path(self.root) / self.env / relative
        return str(path.as_posix())

    def ensure_local(self, path: str) -> Path:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path


class Layer(str, Enum):
    LANDING = "landing"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class LayerPaths:
    """
    Environment-aware lake path builder.

    local:  {LAKE_ROOT}/{layer}/{domain}/{table}
    s3/minio URI style when LAKE_BACKEND is s3|minio
    """

    def __init__(
        self,
        *,
        env: str | None = None,
        root: str | None = None,
        backend: str | None = None,
        bucket: str | None = None,
    ) -> None:
        self.env = (env or os.getenv("PLATFORM_ENV", "local")).lower()
        self.backend = (backend or os.getenv("LAKE_BACKEND", "local")).lower()
        self.root = root or os.getenv("LAKE_ROOT", "./data/lake")
        self.bucket = bucket or os.getenv("LAKE_BUCKET", "data-platform-lake")

    def table_path(self, layer: Layer | str, domain: str, table: str) -> str:
        layer_name = layer.value if isinstance(layer, Layer) else layer
        relative = f"{layer_name}/{domain}/{table}"
        if self.backend in {"s3", "minio"}:
            return f"s3a://{self.bucket}/{self.env}/{relative}"
        path = Path(self.root) / self.env / relative
        return str(path.as_posix())

    def ensure_local(self, path: str) -> Path:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

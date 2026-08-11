from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from platform_dbutils.paths import LayerPaths
from platform_utils.logging import get_logger

logger = get_logger(__name__)


class LakeIO:
    """Lightweight local lake IO (CSV/JSON). Spark/Delta can wrap these paths later."""

    def __init__(self, paths: LayerPaths | None = None) -> None:
        self.paths = paths or LayerPaths()

    def write_json(self, path: str, rows: list[dict[str, Any]]) -> str:
        target = Path(path)
        if target.suffix:
            target.parent.mkdir(parents=True, exist_ok=True)
            file_path = target
        else:
            self.paths.ensure_local(path)
            file_path = Path(path) / "data.json"
        with file_path.open("w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2, default=str)
        logger.info("wrote %s rows -> %s", len(rows), file_path)
        return str(file_path)

    def read_json(self, path: str) -> list[dict[str, Any]]:
        file_path = Path(path)
        if file_path.is_dir():
            file_path = file_path / "data.json"
        with file_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError(f"Expected list JSON at {file_path}")
        return data

    def write_csv(self, path: str, rows: list[dict[str, Any]]) -> str:
        if not rows:
            raise ValueError("Cannot write empty CSV")
        target = Path(path)
        if target.suffix:
            target.parent.mkdir(parents=True, exist_ok=True)
            file_path = target
        else:
            self.paths.ensure_local(path)
            file_path = Path(path) / "data.csv"
        with file_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        logger.info("wrote %s rows -> %s", len(rows), file_path)
        return str(file_path)

    def read_csv(self, path: str) -> list[dict[str, Any]]:
        file_path = Path(path)
        if file_path.is_dir():
            file_path = file_path / "data.csv"
        with file_path.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

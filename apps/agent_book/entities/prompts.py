"""Versioned prompts — YAML is the source, hash goes on every turn."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = APP_ROOT / "config" / "agent" / "templates" / "prompts.yml"


@dataclass(frozen=True)
class Prompt:
    id: str
    body: str
    sha: str


class PromptCatalog:
    def __init__(self, items: dict[str, Prompt]) -> None:
        self._items = items

    def get(self, name: str) -> Prompt:
        try:
            return self._items[name]
        except KeyError as exc:
            raise KeyError(f"unknown prompt: {name}") from exc

    def body(self, name: str) -> str:
        return self.get(name).body

    def meta(self, name: str) -> tuple[str, str]:
        prompt = self.get(name)
        return prompt.id, prompt.sha


@lru_cache(maxsize=1)
def load_catalog(path: str | None = None) -> PromptCatalog:
    source = Path(path) if path else DEFAULT_PATH
    raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    items: dict[str, Prompt] = {}
    for name, spec in raw.items():
        body = str(spec.get("body") or "").strip()
        ident = str(spec.get("id") or f"{name}.v1")
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
        items[str(name)] = Prompt(id=ident, body=body, sha=digest)
    return PromptCatalog(items)


def catalog() -> PromptCatalog:
    return load_catalog()

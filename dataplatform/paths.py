"""Path helpers — anchored lake roots and safe write directories."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    from dataplatform.config import repo_root

    return repo_root()


_APP_SCAFFOLD_DIRS = frozenset({"seeds", "configs", "dags", "scripts", "src"})


def resolve_lake_root(configured: str, *, platform_root: Path | None = None) -> str:
    """Turn lake root config into an absolute path under the repo when relative."""
    root = platform_root or _repo_root()
    path = Path(configured)
    if path.is_absolute():
        return str(path)
    return str((root / path).resolve())


def ensure_write_parent(path: Path | str) -> Path:
    """Create parent dirs for a file write; block stray scaffold folders at repo root."""
    target = Path(path)
    parent = target.parent
    _guard_against_root_scaffold(parent)
    parent.mkdir(parents=True, exist_ok=True)
    return target


def ensure_dir(path: Path | str) -> Path:
    """Create a directory tree; block stray scaffold folders at repo root."""
    target = Path(path)
    _guard_against_root_scaffold(target)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _guard_against_root_scaffold(parent: Path) -> None:
    root = _repo_root().resolve()
    resolved = parent.resolve()
    if resolved.parent == root and resolved.name in _APP_SCAFFOLD_DIRS:
        raise ValueError(
            f"Refusing to create '{resolved.name}/' at repo root. "
            f"Use apps/<app_id>/{resolved.name}/ and set DATA_PLATFORM_APP."
        )

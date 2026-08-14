"""Local dev helpers (cache cleanup, etc.)."""

from __future__ import annotations

import shutil
from pathlib import Path

_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "site-packages",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}


def clean_pycache(root: Path | None = None) -> int:
    """Remove __pycache__ dirs and *.pyc/*.pyo under repo (skips venv)."""
    base = (root or Path.cwd()).resolve()
    removed = 0
    for path in base.rglob("__pycache__"):
        if not path.is_dir() or _should_skip(path):
            continue
        shutil.rmtree(path, ignore_errors=True)
        removed += 1
    for path in base.rglob("*.py[co]"):
        if not path.is_file() or _should_skip(path):
            continue
        path.unlink(missing_ok=True)
        removed += 1
    return removed


def clean_empty_dirs(root: Path | None = None) -> int:
    """Remove empty directories bottom-up (skips venv, caches, etc.)."""
    base = (root or Path.cwd()).resolve()
    removed = 0
    changed = True
    while changed:
        changed = False
        candidates = [
            path
            for path in base.rglob("*")
            if path.is_dir() and not _should_skip(path) and _is_empty_dir(path)
        ]
        for path in sorted(candidates, key=lambda p: len(p.parts), reverse=True):
            try:
                path.rmdir()
                removed += 1
                changed = True
            except OSError:
                continue
    return removed


def clean_workspace(root: Path | None = None) -> dict[str, int]:
    """Remove bytecode cache and empty scaffold directories."""
    base = root or Path.cwd()
    return {
        "pycache": clean_pycache(base),
        "empty_dirs": clean_empty_dirs(base),
    }


def _is_empty_dir(path: Path) -> bool:
    try:
        return not any(path.iterdir())
    except OSError:
        return False


def _should_skip(path: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.parts)

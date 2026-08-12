"""Bootstrap sys.path for Airflow workflow modules."""

from __future__ import annotations

import os
import sys

from runtime import APP_ID, app_root, repo_root

_REPO = repo_root()
_APP = app_root()

for path in (_REPO, _APP):
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("DATA_PLATFORM_ROOT", str(_REPO))
os.environ.setdefault("DATA_PLATFORM_APP", APP_ID)

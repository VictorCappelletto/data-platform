"""YAML config loader — global platform config + per-app config."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    env = os.getenv("DATA_PLATFORM_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1]


def default_app() -> str | None:
    return os.getenv("DATA_PLATFORM_APP") or os.getenv("DATA_PLATFORM_PROJECT")


@dataclass(frozen=True)
class LakeSettings:
    root: str
    backend: str
    bucket: str


@dataclass(frozen=True)
class PlatformSettings:
    environment: str
    lake: LakeSettings
    secrets_backend: str
    aws_region: str
    log_level: str


@dataclass(frozen=True)
class AppSettings:
    """Generic app identity — domain-specific fields live in each app's utils/."""

    app_id: str
    name: str
    lake_prefix: str


# Backward-compatible alias
ProjectSettings = AppSettings


@dataclass(frozen=True)
class DagTaskConfig:
    task_id: str
    callable: str = ""
    orchestrator: str = ""
    upstream: list[str] = field(default_factory=list)

    @property
    def entry_point(self) -> str:
        return self.orchestrator or self.callable


@dataclass(frozen=True)
class DagConfig:
    dag_id: str
    schedule: str
    catchup: bool
    tags: list[str]
    owner: str
    product: str
    tasks: list[DagTaskConfig]
    pool: str | None = None
    retries: int = 0
    retry_delay_minutes: int = 5
    max_active_runs: int | None = None
    max_active_tasks: int | None = None


class ConfigLoader:
    """Load global config/ and app config from apps/<id>/config/."""

    def __init__(
        self,
        root: Path | None = None,
        app: str | None = None,
        project: str | None = None,
    ) -> None:
        self.root = root or repo_root()
        self.app = app or project or default_app()
        self.global_config_dir = self.root / "config"
        if self.app:
            self.app_dir = self.root / "apps" / self.app
            self.config_dir = self.app_dir / "config"
        else:
            self.app_dir = None
            self.config_dir = self.global_config_dir

    # Backward-compatible aliases
    @property
    def project(self) -> str | None:
        return self.app

    @property
    def project_dir(self) -> Path | None:
        return self.app_dir

    @property
    def configs_dir(self) -> Path:
        return self.config_dir

    def read_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Expected mapping in {path}")
        return data

    def constants(self) -> dict[str, Any]:
        global_constants = self.read_yaml(self.global_config_dir / "constants.yml")
        if not self.app_dir:
            return global_constants
        app_constants = self.read_yaml(self.config_dir / "constants.yml")
        merged = dict(global_constants)
        merged.update(app_constants)
        return merged

    def platform(self, environment: str | None = None) -> PlatformSettings:
        env = (environment or os.getenv("PLATFORM_ENV", "local")).lower()
        raw = self.read_yaml(self.global_config_dir / f"platform/{env}.yml")
        lake_raw = raw["lake"]
        secrets = raw.get("secrets", {})
        logging_cfg = raw.get("logging", {})
        return PlatformSettings(
            environment=env,
            lake=LakeSettings(
                root=os.getenv("LAKE_ROOT", lake_raw["root"]),
                backend=os.getenv("LAKE_BACKEND", lake_raw["backend"]),
                bucket=os.getenv("LAKE_BUCKET", lake_raw["bucket"]),
            ),
            secrets_backend=os.getenv("PLATFORM_SECRETS_BACKEND", secrets.get("backend", "env")),
            aws_region=os.getenv("AWS_REGION", secrets.get("region", "us-east-1")),
            log_level=os.getenv("LOG_LEVEL", logging_cfg.get("level", "INFO")),
        )

    def app_settings(self, environment: str | None = None) -> AppSettings:
        if not self.app_dir:
            raise ValueError("app_settings() requires DATA_PLATFORM_APP or app= argument")
        raw = self.read_yaml(self.config_dir / "app.yml")
        app_id = raw.get("app_id") or raw.get("project_id") or self.app
        return AppSettings(
            app_id=app_id,
            name=raw.get("name", app_id),
            lake_prefix=raw.get("lake_prefix", app_id),
        )

    def project_settings(self, environment: str | None = None) -> AppSettings:
        return self.app_settings(environment)

    def _merge_env_overrides(self, raw: dict[str, Any], environment: str) -> dict[str, Any]:
        merged = {k: v for k, v in raw.items() if k != "environments"}
        overrides = raw.get("environments", {}).get(environment, {})
        for key, value in overrides.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        return merged

    def process(self, name: str, environment: str | None = None) -> dict[str, Any]:
        """Load apps/<app>/config/<process>/config_<process>.yml with env overrides."""
        if not self.app_dir:
            raise ValueError("process() requires DATA_PLATFORM_APP or app= argument")
        env = (environment or os.getenv("PLATFORM_ENV", "local")).lower()
        raw = self.read_yaml(self.config_dir / name / f"config_{name}.yml")
        return self._merge_env_overrides(raw, env)

    def orchestration(self, workflow_id: str) -> dict[str, Any]:
        """Load apps/<app>/config/orchestration/<workflow_id>.yml registry."""
        if not self.app_dir:
            raise ValueError("orchestration() requires DATA_PLATFORM_APP or app= argument")
        return self.read_yaml(self.config_dir / f"orchestration/{workflow_id}.yml")

    def dag(self, dag_id: str) -> DagConfig:
        workflow_path = self.config_dir / f"workflows/{dag_id}.yml"
        legacy_path = self.config_dir / f"dags/{dag_id}.yml"
        raw = self.read_yaml(workflow_path if workflow_path.exists() else legacy_path)
        tasks = [
            DagTaskConfig(
                task_id=t["task_id"],
                callable=t.get("callable", ""),
                orchestrator=t.get("orchestrator", ""),
                upstream=list(t.get("upstream", [])),
            )
            for t in raw["tasks"]
        ]
        return DagConfig(
            dag_id=raw["dag_id"],
            schedule=raw["schedule"],
            catchup=bool(raw.get("catchup", False)),
            tags=list(raw.get("tags", [])),
            owner=raw.get("owner", "data-platform"),
            product=raw.get("product", dag_id),
            tasks=tasks,
            pool=raw.get("pool"),
            retries=int(raw.get("retries", 0)),
            retry_delay_minutes=int(raw.get("retry_delay_minutes", 5)),
            max_active_runs=raw.get("max_active_runs"),
            max_active_tasks=raw.get("max_active_tasks"),
        )

    def resolve_path(self, relative: str) -> Path:
        return self.root / relative

    def resolve_app_path(self, relative: str) -> Path:
        if not self.app_dir:
            raise ValueError("resolve_app_path() requires an app context")
        return self.app_dir / relative

    def resolve_project_path(self, relative: str) -> Path:
        return self.resolve_app_path(relative)

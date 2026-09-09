"""Lake mount + local/ADLS I/O + Spark path helpers (Windows)."""

from __future__ import annotations

import csv
import io
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class OlistLakeMount:
    """Single class for ADLS zones, path resolution and lake file I/O."""

    def __init__(
        self,
        *,
        backend: str | None = None,
        lake_root: str | None = None,
        environment: str | None = None,
        lake_prefix: str = "ingestion_azure",
        storage_account: str | None = None,
        lake_config: dict[str, Any] | None = None,
    ) -> None:
        self._cfg = lake_config or self._load_lake_config()
        self.zones: list[str] = list(self._cfg["zones"])
        adls = self._cfg["adls"]
        self._adls_pattern = re.compile(adls["uri_pattern"])
        self._adls_zone_uri = adls["zone_uri"]
        self._adls_account_url = adls["account_url"]
        self._adls_schemes = tuple(f"{s}://" for s in adls.get("schemes", ["abfss", "abfs"]))

        self.backend = (backend or os.getenv("OLIST_LAKE_BACKEND", "local")).lower()
        self.lake_root = lake_root or self._default_lake_root()
        self.environment = (environment or os.getenv("PLATFORM_ENV", "local")).lower()
        self.lake_prefix = lake_prefix
        self.storage_account = storage_account or os.getenv("AZURE_STORAGE_ACCOUNT", "")

    @classmethod
    def _load_lake_config(cls) -> dict[str, Any]:
        from dataplatform.config import ConfigLoader

        loader = ConfigLoader()
        if loader.app_dir:
            raw = loader.read_yaml(loader.config_dir / "app.yml")
            lake = raw.get("lake")
            if isinstance(lake, dict) and "zones" in lake and "adls" in lake:
                return lake
        raise ValueError("lake config missing in apps/ingestion_azure/config/app.yml")

    @staticmethod
    def _default_lake_root() -> str:
        from dataplatform.config import repo_root
        from dataplatform.paths import resolve_lake_root

        override = os.getenv("LAKE_ROOT")
        if override:
            return resolve_lake_root(override)
        platform_root = os.getenv("DATA_PLATFORM_ROOT")
        if platform_root:
            return resolve_lake_root("data/lake", platform_root=Path(platform_root))
        return resolve_lake_root("data/lake", platform_root=repo_root())

    def _validate_zone(self, zone: str) -> str:
        if zone not in self.zones:
            raise ValueError(f"Unknown lake zone {zone!r} — expected one of {self.zones}")
        return zone

    def zone_uri(self, zone: str) -> str:
        zone = self._validate_zone(zone)
        if self.backend == "adls":
            if not self.storage_account:
                raise ValueError("AZURE_STORAGE_ACCOUNT required when OLIST_LAKE_BACKEND=adls")
            return self._adls_zone_uri.format(zone=zone, account=self.storage_account)
        base = Path(self.lake_root) / self.environment / self.lake_prefix / zone
        return str(base.as_posix())

    def file_path(self, zone: str, filename: str) -> str:
        uri = self.zone_uri(zone)
        if self.backend == "adls":
            return f"{uri}{filename}"
        path = Path(uri) / filename
        return str(path.as_posix())

    def _is_adls(self, path: str) -> bool:
        return path.startswith(self._adls_schemes)

    def _parse_abfss(self, uri: str) -> tuple[str, str, str]:
        match = self._adls_pattern.match(uri)
        if not match:
            raise ValueError(f"Invalid ADLS URI (check app.yml lake.adls.uri_pattern): {uri}")
        return match.group("account"), match.group("container"), match.group("path")

    def _adls_client(self, account: str):
        try:
            from azure.identity import DefaultAzureCredential
            from azure.storage.filedatalake import DataLakeServiceClient
        except ImportError as exc:
            raise RuntimeError(
                "ADLS requires azure-identity and azure-storage-file-datalake. "
                "pip install azure-identity azure-storage-file-datalake"
            ) from exc
        credential = DefaultAzureCredential(
            exclude_interactive_browser_credential=True,
            exclude_shared_token_cache_credential=True,
        )
        return DataLakeServiceClient(
            account_url=self._adls_account_url.format(account=account),
            credential=credential,
        )

    def _file_client(self, account: str, container: str, blob: str):
        fs = self._adls_client(account).get_file_system_client(container)
        return fs.get_file_client(blob)

    def read_csv(self, path: str) -> list[dict[str, Any]]:
        if self._is_adls(path):
            account, container, blob = self._parse_abfss(path)
            client = self._file_client(account, container, blob)
            text = client.download_file().readall().decode("utf-8-sig")
            return list(csv.DictReader(io.StringIO(text)))
        with Path(path).open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def write_csv(self, path: str, rows: list[dict[str, Any]]) -> str:
        if not rows:
            raise ValueError(f"Cannot write empty CSV: {path}")
        if self._is_adls(path):
            account, container, blob = self._parse_abfss(path)
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
            file_client = self._file_client(account, container, blob)
            file_client.upload_data(buf.getvalue().encode("utf-8"), overwrite=True)
            return path
        from dataplatform.paths import ensure_write_parent

        target = ensure_write_parent(path)
        with target.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return str(target)

    def write_parquet(self, path: str, rows: list[dict[str, Any]]) -> str:
        if not rows:
            raise ValueError(f"Cannot write empty parquet: {path}")
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError(
                "pyarrow is required for processing zone. pip install 'data-platform[azure]'"
            ) from exc
        if self._is_adls(path):
            account, container, blob = self._parse_abfss(path)
            buf = io.BytesIO()
            pq.write_table(pa.Table.from_pylist(rows), buf)
            file_client = self._file_client(account, container, blob)
            file_client.upload_data(buf.getvalue(), overwrite=True)
            return path
        from dataplatform.paths import ensure_write_parent

        target = ensure_write_parent(path)
        pq.write_table(pa.Table.from_pylist(rows), target)
        return str(target)

    def read_parquet(self, path: str) -> list[dict[str, Any]]:
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError(
                "pyarrow is required for processing zone. pip install 'data-platform[azure]'"
            ) from exc
        if self._is_adls(path):
            account, container, blob = self._parse_abfss(path)
            client = self._file_client(account, container, blob)
            data = client.download_file().readall()
            return pq.read_table(io.BytesIO(data)).to_pylist()
        return pq.read_table(path).to_pylist()

    def spark_data_path(self, zone: str, filename: str) -> str:
        raw = self.file_path(zone, filename)
        if self.backend == "adls":
            return raw
        path = Path(raw).resolve()
        path = _windows_short_path(path)
        uri = path.as_uri()
        return uri.replace("\\", "/") if os.name == "nt" else uri


def _windows_short_path(path: Path | str) -> Path | str:
    if os.name != "nt":
        return path
    try:
        import ctypes

        buf = ctypes.create_unicode_buffer(512)
        result = ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, 512)
        if result and buf.value:
            return Path(buf.value) if isinstance(path, Path) else buf.value
    except Exception:
        pass
    return path


def ensure_spark_friendly_lake_root(lake_root: str) -> str:
    override = os.getenv("SPARK_LAKE_ROOT")
    if override:
        return override
    root = Path(lake_root).resolve()
    if root.as_posix().isascii():
        return str(root)
    staging = Path(os.getenv("TEMP", "C:/temp")) / "data-platform-spark-lake"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(root, staging)
    return str(staging)


def _repo_root() -> Path:
    from dataplatform.config import repo_root

    return repo_root()


def default_hadoop_home(repo_root: Path | None = None) -> Path:
    root = repo_root or _repo_root()
    return root / "docker" / "spark" / "hadoop"


def configure_hadoop_windows(repo_root: Path | None = None) -> str | None:
    if os.name != "nt":
        return os.getenv("HADOOP_HOME")
    hadoop_home = Path(os.getenv("HADOOP_HOME") or default_hadoop_home(repo_root))
    winutils = hadoop_home / "bin" / "winutils.exe"
    if not winutils.is_file():
        hadoop_home = default_hadoop_home(repo_root)
        winutils = hadoop_home / "bin" / "winutils.exe"
        if not winutils.is_file():
            raise RuntimeError(
                "winutils.exe not found. Run:\n"
                "  powershell -ExecutionPolicy Bypass -File docker/spark/setup-hadoop-windows.ps1"
            )
    os.environ["HADOOP_HOME"] = str(_windows_short_path(str(hadoop_home)))
    bin_dir = hadoop_home / "bin"
    entry = str(bin_dir)
    path = os.environ.get("PATH", "")
    if entry not in path.split(os.pathsep):
        os.environ["PATH"] = entry + os.pathsep + path
    java_home = os.getenv("JAVA_HOME")
    if java_home:
        src = bin_dir / "hadoop.dll"
        if src.is_file():
            dest = Path(java_home) / "bin" / "hadoop.dll"
            try:
                if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
                    shutil.copy2(src, dest)
            except OSError:
                pass
    return os.environ["HADOOP_HOME"]


def spark_hadoop_configs(repo_root: Path | None = None) -> dict[str, str]:
    hadoop_home = configure_hadoop_windows(repo_root)
    if not hadoop_home:
        return {}
    home = str(_windows_short_path(hadoop_home)).replace("\\", "/")
    bin_dir = str(_windows_short_path(str(Path(hadoop_home) / "bin"))).replace("\\", "/")
    java_opts = f'-Dhadoop.home.dir="{home}" -Djava.library.path="{bin_dir}"'
    return {
        "spark.hadoop.hadoop.home.dir": home,
        "spark.driver.extraJavaOptions": java_opts,
        "spark.executor.extraJavaOptions": java_opts,
    }


def ensure_winutils_chmod(path: str) -> None:
    if os.name != "nt":
        return
    configure_hadoop_windows()
    winutils = Path(os.environ["HADOOP_HOME"]) / "bin" / "winutils.exe"
    if winutils.is_file():
        subprocess.run(
            [str(winutils), "chmod", "-R", "777", path],
            check=False,
            capture_output=True,
        )

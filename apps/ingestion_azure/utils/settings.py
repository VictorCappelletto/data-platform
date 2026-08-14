"""Azure / Olist app settings — SQL Server and lake config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataplatform.config import ConfigLoader


@dataclass(frozen=True)
class SqlServerSettings:
    server: str
    database: str
    user: str
    password: str
    driver: str
    trust_server_certificate: bool

    @property
    def connection_string(self) -> str:
        trust = "yes" if self.trust_server_certificate else "no"
        return (
            f"Driver={{{self.driver}}};"
            f"Server={self.server};"
            f"Database={self.database};"
            f"Uid={self.user};"
            f"Pwd={self.password};"
            f"TrustServerCertificate={trust};"
        )


@dataclass(frozen=True)
class AzureAppSettings:
    app_id: str
    name: str
    lake_prefix: str
    sql_server: SqlServerSettings


def bind_azure_settings(instance: object, environment: str | None = None) -> None:
    """Replace generic app settings with AzureAppSettings on a process base instance."""
    loader = instance.loader  # type: ignore[attr-defined]
    instance.app = load_app_settings(loader, environment)  # type: ignore[attr-defined]
    instance.project = instance.app  # type: ignore[attr-defined]


def load_app_settings(
    loader: ConfigLoader,
    environment: str | None = None,
) -> AzureAppSettings:
    if not loader.app_dir:
        raise ValueError("load_app_settings() requires DATA_PLATFORM_APP or app= argument")
    raw = loader.read_yaml(loader.config_dir / "app.yml")
    app_id = raw.get("app_id") or raw.get("project_id") or loader.app
    extraction = loader.process("extraction", environment)
    sql_raw = extraction.get("sql_server", raw.get("sql_server", {}))
    return AzureAppSettings(
        app_id=app_id,
        name=raw.get("name", app_id),
        lake_prefix=raw.get("lake_prefix", app_id),
        sql_server=SqlServerSettings(
            server=os.getenv("MSSQL_SERVER", sql_raw.get("server", "localhost,1433")),
            database=os.getenv("MSSQL_DATABASE", sql_raw.get("database", "olist")),
            user=os.getenv("MSSQL_USER", sql_raw.get("user", "sa")),
            password=os.getenv("MSSQL_SA_PASSWORD", sql_raw.get("password", "")),
            driver=os.getenv(
                "MSSQL_ODBC_DRIVER",
                sql_raw.get("driver", "ODBC Driver 18 for SQL Server"),
            ),
            trust_server_certificate=os.getenv(
                "MSSQL_TRUST_SERVER_CERTIFICATE", str(sql_raw.get("trust_server_certificate", True))
            ).lower()
            in {"1", "true", "yes"},
        ),
    )

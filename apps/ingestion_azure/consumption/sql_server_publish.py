"""
Publish lake layers into SQL Server medallion schemas (bronze / silver / gold).

  landing csv         ->  olist_dw.bronze.{table}
  processing parquet  ->  olist_dw.silver.{table}
  curated csv         ->  olist_dw.gold.{table}

Power BI Desktop reads gold.customers_RJ (and silver.* / bronze.* for exploration).
"""

from __future__ import annotations

import re
from typing import Any

from consumption.base import ConsumptionBase
from transformation.io import OlistLakeMount


class SqlServerPublisher(ConsumptionBase):
    def __init__(self, domain_key: str = "olist", environment: str | None = None) -> None:
        super().__init__(domain_key, environment)
        sql_cfg = self.product_config.get("sql", {})
        self._ident_pattern = re.compile(sql_cfg.get("identifier_pattern", r"^[A-Za-z_][A-Za-z0-9_]*$"))
        self._column_sql_type = sql_cfg.get("column_type", "NVARCHAR(MAX)")
        transform_cfg = self.loader.process("transformation", environment)
        self.transform_config = transform_cfg.get(domain_key, {})
        self.mount = OlistLakeMount(
            lake_prefix=self.app.lake_prefix,
            environment=self.platform.environment,
        )

    def publish_table(self, layer: str, table: str) -> dict[str, Any]:
        """Read one lake file and replace the matching SQL schema.table."""
        layer_cfg = self.product_config.get("layers", {})
        if layer not in layer_cfg:
            raise ValueError(f"Unknown layer '{layer}' — expected one of {list(layer_cfg)}")
        if not self._ident_pattern.match(layer) or not self._ident_pattern.match(table):
            raise ValueError(f"Invalid SQL identifier: {layer}.{table}")

        cfg = layer_cfg[layer]
        zone_name = cfg.get("lake_zone", layer)
        fmt = cfg.get("format", "csv")
        path = self.mount.file_path(zone_name, f"{table}.{fmt}")
        rows = self.mount.read_parquet(path) if fmt == "parquet" else self.mount.read_csv(path)

        sql = self.app.sql_server
        master_cs = (
            f"Driver={{{sql.driver}}};Server={sql.server};Database=master;"
            f"Uid={sql.user};Pwd={sql.password};TrustServerCertificate=yes;"
        )
        target_cs = (
            f"Driver={{{sql.driver}}};Server={sql.server};"
            f"Database={self.consumption_database};"
            f"Uid={sql.user};Pwd={sql.password};TrustServerCertificate=yes;"
        )
        try:
            import pyodbc
        except ImportError as exc:
            raise RuntimeError("pyodbc required. pip install 'data-platform[olist]'") from exc

        db = self.consumption_database
        with pyodbc.connect(master_cs, autocommit=True) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{db}')
                BEGIN CREATE DATABASE [{db}]; END
                """
            )

        qualified = f"[{layer}].[{table}]"
        if not rows:
            self.logger.warning("%s source empty — skipping publish", qualified)
            return {
                "layer": layer,
                "table": table,
                "rows": 0,
                "database": db,
                "qualified_name": f"{db}.{layer}.{table}",
            }

        with pyodbc.connect(target_cs, autocommit=False) as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'{layer}')
                BEGIN EXEC('CREATE SCHEMA [{layer}]'); END
                """
            )
            columns = list(rows[0].keys())
            col_defs = ", ".join(f"[{col}] {self._column_sql_type} NULL" for col in columns)
            cur.execute(f"IF OBJECT_ID(N'{layer}.{table}', N'U') IS NOT NULL DROP TABLE {qualified};")
            cur.execute(f"CREATE TABLE {qualified} ({col_defs});")
            col_list = ", ".join(f"[{col}]" for col in columns)
            placeholders = ", ".join("?" for _ in columns)
            insert_sql = f"INSERT INTO {qualified} ({col_list}) VALUES ({placeholders})"
            values = [[row.get(col) for col in columns] for row in rows]
            cur.fast_executemany = True
            cur.executemany(insert_sql, values)
            conn.commit()
            self.logger.info("published %s rows -> %s.%s", len(values), db, qualified)
            return {
                "layer": layer,
                "table": table,
                "rows": len(values),
                "database": db,
                "qualified_name": f"{db}.{layer}.{table}",
            }

    def run(self) -> dict[str, Any]:
        """Publish landing → bronze, processing → silver, curated → gold."""
        transform = self.transform_config
        base_tables = list(transform.get("tables", []))
        filtered_tables = [
            rule["output"]
            for rules in transform.get("filters", {}).values()
            for rule in rules
        ]
        layer_tables = {
            "bronze": base_tables,
            "silver": base_tables + filtered_tables,
            "gold": filtered_tables,
        }

        layers: dict[str, list[dict[str, Any]]] = {}
        all_results: list[dict[str, Any]] = []
        for layer, tables in layer_tables.items():
            layer_results = [self.publish_table(layer, name) for name in tables]
            layers[layer] = layer_results
            all_results.extend(layer_results)

        return {
            "database": self.consumption_database,
            "layers": layers,
            "total_rows": sum(r["rows"] for r in all_results),
        }


def run_publish_curated(**kwargs: Any) -> dict[str, Any]:
    """Orchestrator entry point."""
    env = kwargs.get("environment")
    return SqlServerPublisher(environment=env).run()

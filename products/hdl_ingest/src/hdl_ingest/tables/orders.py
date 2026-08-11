from __future__ import annotations

from typing import Any

from hdl_ingest.tables.base import LakeTable


class OrdersTable(LakeTable):
    domain = "orders"
    table = "orders"

    def to_bronze(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bronze: list[dict[str, Any]] = []
        for row in rows:
            bronze.append(
                {
                    "order_id": str(row["order_id"]).strip(),
                    "customer_id": str(row["customer_id"]).strip(),
                    "amount": float(row["amount"]),
                    "status": str(row["status"]).strip().lower(),
                    "country": str(row.get("country", "BR")).strip().upper(),
                    "event_ts": row["event_ts"],
                    "load_at": row["load_at"],
                }
            )
        return bronze

    def to_silver(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate by order_id keeping latest load_at and set is_current."""
        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            current = by_id.get(row["order_id"])
            if current is None or row["load_at"] >= current["load_at"]:
                by_id[row["order_id"]] = dict(row)

        silver: list[dict[str, Any]] = []
        for row in rows:
            latest = by_id[row["order_id"]]
            out = dict(row)
            out["is_current"] = (
                row["load_at"] == latest["load_at"]
                and row["event_ts"] == latest["event_ts"]
                and row["status"] == latest["status"]
            )
            # Mark only one current row per order_id (the chosen latest)
            if out["is_current"] and row is not latest and row["order_id"] in by_id:
                # compare object identity against stored latest snapshot values
                out["is_current"] = (
                    row["load_at"] == latest["load_at"]
                    and abs(float(row["amount"]) - float(latest["amount"])) < 1e-9
                )
            silver.append(out)

        # Normalize: exactly one is_current=True per order_id
        seen: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for row in sorted(silver, key=lambda r: (r["order_id"], r["load_at"]), reverse=True):
            flag = row["order_id"] not in seen
            if flag:
                seen.add(row["order_id"])
            row = dict(row)
            row["is_current"] = flag
            normalized.append(row)
        return normalized

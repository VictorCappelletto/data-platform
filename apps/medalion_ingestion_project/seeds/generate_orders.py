"""Generate synthetic orders CSV for bulk/demo runs (no PII, reproducible)."""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

STATUSES = ("completed", "pending", "cancelled")
STATUS_WEIGHTS = (0.72, 0.18, 0.10)


def generate_rows(
    *,
    count: int,
    customers: int,
    start: date,
    days: int,
    duplicate_rate: float,
    seed: int,
) -> list[dict[str, str]]:
    rng = random.Random(seed)
    rows: list[dict[str, str]] = []
    for i in range(count):
        order_num = i + 1
        order_id = f"o-{order_num:06d}"
        customer_id = f"c-{rng.randint(1, customers):04d}"
        amount = round(rng.uniform(5.0, 2500.0), 2)
        status = rng.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
        event_day = start + timedelta(days=rng.randint(0, max(days - 1, 0)))
        hour = rng.randint(0, 23)
        minute = rng.randint(0, 59)
        event_ts = datetime(event_day.year, event_day.month, event_day.day, hour, minute).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        load_at = (event_day + timedelta(days=rng.randint(0, 1))).isoformat()
        rows.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "amount": f"{amount:.2f}",
                "status": status,
                "country": "BR",
                "event_ts": event_ts,
                "load_at": load_at,
            }
        )

    dupes = int(count * duplicate_rate)
    for _ in range(dupes):
        base = rng.choice(rows[:count])
        revised = dict(base)
        revised["status"] = rng.choice(("completed", "pending"))
        revised["load_at"] = (
            date.fromisoformat(base["load_at"]) + timedelta(days=rng.randint(1, 3))
        ).isoformat()
        rows.append(revised)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "order_id",
                "customer_id",
                "amount",
                "status",
                "country",
                "event_ts",
                "load_at",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic orders bulk seed")
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--customers", type=int, default=2_000)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--duplicate-rate", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("orders_bulk.csv"),
    )
    args = parser.parse_args()
    start = date.today() - timedelta(days=args.days)
    rows = generate_rows(
        count=args.count,
        customers=args.customers,
        start=start,
        days=args.days,
        duplicate_rate=args.duplicate_rate,
        seed=args.seed,
    )
    write_csv(args.output, rows)
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()

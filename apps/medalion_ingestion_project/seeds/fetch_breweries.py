"""Download Open Brewery DB records into a local JSON fixture (free, ODbL)."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://api.openbrewerydb.org/v1/breweries"


def fetch_all(*, per_page: int = 50, pause_s: float = 0.15) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        url = f"{DEFAULT_URL}?per_page={per_page}&page={page}"
        request = urllib.request.Request(url, headers={"User-Agent": "data-platform-portfolio/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                batch = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                break
            raise
        if not batch:
            break
        rows.extend(batch)
        print(f"page {page}: +{len(batch)} total={len(rows)}")
        if len(batch) < per_page:
            break
        page += 1
        time.sleep(pause_s)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Open Brewery DB bulk fixture")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("breweries_bulk.json"),
    )
    args = parser.parse_args()
    rows = fetch_all()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(rows)} breweries to {args.output}")


if __name__ == "__main__":
    main()

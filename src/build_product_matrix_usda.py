"""Download branded products from USDA FoodData Central and flag additive presence."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import ADDITIVE_PATTERNS
from ingredient_match import detect_additives
from product_sources import DEFAULT_USDA_FDC_API_KEY, UpstreamRateLimited

FDC_LIST = "https://api.nal.usda.gov/fdc/v1/foods/list"


def fetch_list_page(page_number: int, page_size: int, api_key: str) -> list[dict[str, Any]]:
    params = {
        "api_key": api_key,
        "dataType": "Branded",
        "pageNumber": page_number,
        "pageSize": page_size,
    }
    r = requests.get(FDC_LIST, params=params, timeout=30)
    if r.status_code == 429:
        raise UpstreamRateLimited("USDA FoodData Central rate limited (HTTP 429).")
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        return []
    return data


def build_usda_matrix(
    pages: int,
    page_size: int,
    sleep_s: float,
    api_key: str,
) -> pd.DataFrame:
    api_key = (api_key or "").strip() or DEFAULT_USDA_FDC_API_KEY
    rows: list[dict[str, Any]] = []
    for p in range(1, pages + 1):
        foods = fetch_list_page(p, page_size, api_key=api_key)
        for f in foods:
            if not isinstance(f, dict):
                continue
            fdc_id = f.get("fdcId")
            if not fdc_id:
                continue
            ing = (f.get("ingredients") or "").strip()
            name = (f.get("description") or "").strip()
            flags = detect_additives(ing, ADDITIVE_PATTERNS)
            rows.append(
                {
                    "product_id": f"usda_{fdc_id}",
                    "product_name": name,
                    **flags,
                }
            )
        if sleep_s > 0:
            time.sleep(sleep_s)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch USDA Branded foods and additive flags.")
    parser.add_argument("--pages", type=int, default=3, help="Number of pages to fetch.")
    parser.add_argument("--page-size", type=int, default=50, help="Rows per page (max ~200).")
    parser.add_argument("--sleep", type=float, default=0.6, help="Seconds between page requests.")
    parser.add_argument("--api-key", type=str, default=DEFAULT_USDA_FDC_API_KEY, help="FDC API key.")
    parser.add_argument("--output", type=str, default="", help="Optional output CSV path.")
    args = parser.parse_args()

    df = build_usda_matrix(args.pages, args.page_size, args.sleep, api_key=args.api_key)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        print(f"Saved {len(df)} rows to {out}")
    else:
        print(f"Fetched {len(df)} USDA rows")


if __name__ == "__main__":
    main()


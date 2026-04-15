"""Download product ingredient lists from Open Food Facts and flag additive presence."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import ADDITIVE_PATTERNS, DATA_DIR, PRODUCTS_CSV
from ingredient_match import detect_additives

# Prefer API v2 search; cgi endpoint is sometimes rate-limited or returns 503.
SEARCH_URL_V2 = "https://world.openfoodfacts.net/api/v2/search"
SEARCH_URL_V1 = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_HEADERS = {
    "User-Agent": "GutSafetyAI/1.0 (Open Food Facts API; local training)",
}


def fetch_page(page: int, page_size: int) -> list[dict]:
    v2_params = {
        "page": page,
        "page_size": page_size,
        "fields": "code,product_name,ingredients_text",
    }
    try:
        r2 = requests.get(SEARCH_URL_V2, params=v2_params, timeout=45, headers=OFF_HEADERS)
        if r2.ok:
            data = r2.json()
            prods = data.get("products") if isinstance(data, dict) else None
            if isinstance(prods, list):
                return prods
    except requests.RequestException:
        pass

    v1_params = {
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page": page,
        "page_size": page_size,
        "fields": "code,product_name,ingredients_text",
    }
    r1 = requests.get(SEARCH_URL_V1, params=v1_params, timeout=60, headers=OFF_HEADERS)
    r1.raise_for_status()
    return r1.json().get("products", [])


def build_matrix(pages: int, page_size: int, sleep_s: float) -> pd.DataFrame:
    rows: list[dict] = []
    for p in range(1, pages + 1):
        products = fetch_page(p, page_size)
        for prod in products:
            code = prod.get("code")
            if not code:
                continue
            name = prod.get("product_name") or ""
            ing = prod.get("ingredients_text")
            flags = detect_additives(ing, ADDITIVE_PATTERNS)
            row: dict = {
                "product_id": str(code),
                "product_name": name,
                **flags,
            }
            rows.append(row)
        if sleep_s > 0:
            time.sleep(sleep_s)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OFF products and additive flags.")
    parser.add_argument("--pages", type=int, default=5, help="Number of API pages to fetch.")
    parser.add_argument("--page-size", type=int, default=100, help="Products per page (max ~100).")
    parser.add_argument("--sleep", type=float, default=0.4, help="Seconds between page requests.")
    parser.add_argument("--output", type=str, default=str(PRODUCTS_CSV), help="Output CSV path.")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = build_matrix(args.pages, args.page_size, args.sleep)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows to {out}")


if __name__ == "__main__":
    main()

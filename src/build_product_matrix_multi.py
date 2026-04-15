"""Build additive-flag training table from Open Food Facts + USDA branded."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import DATA_DIR, PRODUCTS_CSV
from build_product_matrix import build_matrix as build_off_matrix
from build_product_matrix_usda import build_usda_matrix
from product_sources import DEFAULT_USDA_FDC_API_KEY


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OFF+USDA products and additive flags.")

    parser.add_argument(
        "--sources",
        type=str,
        default="off,usda",
        help="Comma-separated: off,usda",
    )

    parser.add_argument("--off-pages", type=int, default=5)
    parser.add_argument("--off-page-size", type=int, default=100)
    parser.add_argument("--off-sleep", type=float, default=0.4)

    parser.add_argument("--usda-pages", type=int, default=3)
    parser.add_argument("--usda-page-size", type=int, default=50)
    parser.add_argument("--usda-sleep", type=float, default=0.6)
    parser.add_argument("--usda-api-key", type=str, default=DEFAULT_USDA_FDC_API_KEY)

    parser.add_argument("--output", type=str, default=str(PRODUCTS_CSV))
    args = parser.parse_args()

    sources = {s.strip().lower() for s in (args.sources or "").split(",") if s.strip()}
    frames: list[pd.DataFrame] = []

    if "off" in sources:
        frames.append(build_off_matrix(args.off_pages, args.off_page_size, args.off_sleep))
    if "usda" in sources:
        frames.append(build_usda_matrix(args.usda_pages, args.usda_page_size, args.usda_sleep, api_key=args.usda_api_key))

    if not frames:
        raise SystemExit("No sources selected. Use --sources off,usda")

    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["product_id"], keep="first")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows to {out}")


if __name__ == "__main__":
    main()


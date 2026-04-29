"""Automate data collection + retraining in a loop.

This script incrementally fetches additive-flag rows from:
- Open Food Facts (OFF)
- USDA FoodData Central (Branded)

It appends/dedupes into data/products_additives.csv and periodically retrains:
- sklearn model (fallback)
- PyTorch NN model (primary)
"""

from __future__ import annotations

import argparse
import random
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import requests

_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from build_product_matrix import build_matrix as build_off_matrix
from build_product_matrix_usda import build_usda_matrix
from config import DATA_DIR, PRODUCTS_CSV


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(_ROOT))


def _read_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _merge(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    if existing is None or existing.empty:
        df = new.copy()
    elif new is None or new.empty:
        df = existing.copy()
    else:
        df = pd.concat([existing, new], ignore_index=True)
    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].astype(str)
        df = df.drop_duplicates(subset=["product_id"], keep="first")
    return df


def _fetch_with_backoff(fetch_fn, max_retries: int, base_sleep_s: float) -> pd.DataFrame:
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fetch_fn()
        except (requests.RequestException, Exception) as e:
            last_err = e
            sleep_s = base_sleep_s * (2**attempt) + random.uniform(0.0, 0.25)
            print(f"Fetch failed ({type(e).__name__}): {e}. Sleeping {sleep_s:.2f}s then retrying…", flush=True)
            time.sleep(sleep_s)
    raise SystemExit(f"Giving up after retries. Last error: {last_err}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-fetch OFF+USDA and retrain models repeatedly.")
    parser.add_argument("--rounds", type=int, default=20, help="How many fetch rounds to run.")
    parser.add_argument("--retrain-every", type=int, default=2, help="Retrain after N rounds.")

    parser.add_argument("--off-pages-per-round", type=int, default=1)
    parser.add_argument("--off-page-size", type=int, default=100)
    parser.add_argument("--off-sleep", type=float, default=0.4)
    parser.add_argument("--off-start-page", type=int, default=1)

    parser.add_argument("--usda-pages-per-round", type=int, default=1)
    parser.add_argument("--usda-page-size", type=int, default=100)
    parser.add_argument("--usda-sleep", type=float, default=0.6)
    parser.add_argument("--usda-start-page", type=int, default=1)
    parser.add_argument("--usda-api-key", type=str, default="", help="Optional override; else uses embedded key.")

    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--backoff", type=float, default=1.0, help="Base seconds for exponential backoff.")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = _read_existing(PRODUCTS_CSV)

    off_page = int(args.off_start_page)
    usda_page = int(args.usda_start_page)

    python = sys.executable

    for r in range(1, int(args.rounds) + 1):
        print(f"\n=== Round {r}/{args.rounds} ===", flush=True)

        off_df = _fetch_with_backoff(
            lambda: build_off_matrix(args.off_pages_per_round, args.off_page_size, args.off_sleep),
            max_retries=args.max_retries,
            base_sleep_s=args.backoff,
        )
        # build_off_matrix always starts at page 1 internally; to avoid overcomplicating, we just keep adding
        # more random-ish samples over time. (OFF search ordering changes frequently anyway.)

        usda_key = (args.usda_api_key or "").strip() or None
        usda_df = _fetch_with_backoff(
            lambda: build_usda_matrix(
                args.usda_pages_per_round,
                args.usda_page_size,
                args.usda_sleep,
                api_key=usda_key,
            ),
            max_retries=args.max_retries,
            base_sleep_s=args.backoff,
        )

        before = len(existing) if not existing.empty else 0
        combined = _merge(existing, _merge(off_df, usda_df))
        after = len(combined) if not combined.empty else 0
        added = after - before

        combined.to_csv(PRODUCTS_CSV, index=False)
        existing = combined
        print(f"Saved {after} rows to {PRODUCTS_CSV} (+{added} new)", flush=True)

        if int(args.retrain_every) > 0 and (r % int(args.retrain_every) == 0):
            print("Retraining models…", flush=True)
            _run([python, str(_SRC / "build_training_table.py")])
            _run([python, str(_SRC / "train_microbiome_model.py")])
            _run([python, str(_SRC / "train_microbiome_nn.py")])

    print("\nDone.", flush=True)


if __name__ == "__main__":
    main()


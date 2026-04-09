"""Aggregate literature-based additive effects into per-product microbiome label vectors."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import (
    ADDITIVES_CSV,
    DATA_DIR,
    LABELS_CSV,
    PRODUCTS_CSV,
    TARGET_COLUMNS,
)


def main() -> None:
    add = pd.read_csv(ADDITIVES_CSV)
    prod = pd.read_csv(PRODUCTS_CSV)
    add["col_name"] = add["additive"].str.strip().str.lower()

    feature_cols = list(add["col_name"])
    rows: list[dict] = []
    for _, p in prod.iterrows():
        effects: dict = {
            "product_id": p["product_id"],
            "product_name": p.get("product_name", ""),
        }
        for col in TARGET_COLUMNS:
            effects[col] = 0.0

        for _, a in add.iterrows():
            col = a["col_name"]
            if col not in p:
                continue
            if int(p[col]) != 1:
                continue
            for tcol in TARGET_COLUMNS:
                effects[tcol] += float(a[tcol])

        rows.append(effects)

    df = pd.DataFrame(rows)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(LABELS_CSV, index=False)
    print(f"Saved {len(df)} rows to {LABELS_CSV}")
    print("Feature columns used:", feature_cols)


if __name__ == "__main__":
    main()

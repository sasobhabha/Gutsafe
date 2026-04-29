"""Train multi-output model: additive presence -> microbiome impact vector."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import ADDITIVES_CSV, LABELS_CSV, MODEL_PATH, MODELS_DIR, PRODUCTS_CSV, TARGET_COLUMNS


def feature_columns_from_additives() -> list[str]:
    add = pd.read_csv(ADDITIVES_CSV)
    return [str(x).strip().lower() for x in add["additive"].tolist()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    feature_cols = feature_columns_from_additives()
    prod = pd.read_csv(PRODUCTS_CSV)
    labels = pd.read_csv(LABELS_CSV)
    df = prod.merge(labels, on="product_id", suffixes=("", "_y"))
    if "product_name_y" in df.columns:
        df.drop(columns=["product_name_y"], inplace=True)

    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing feature columns in products CSV: {missing}")

    X = df[feature_cols].astype(float)
    Y = df[TARGET_COLUMNS].astype(float)

    if len(df) < 10:
        print("Warning: very few products; metrics may be unstable.")

    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=args.test_size, random_state=args.seed
    )

    base = GradientBoostingRegressor(random_state=args.seed, max_depth=4, n_estimators=200)
    model = MultiOutputRegressor(base)
    model.fit(X_train, Y_train)
    pred = model.predict(X_test)

    r2 = r2_score(Y_test, pred, multioutput="raw_values")
    mae = mean_absolute_error(Y_test, pred, multioutput="raw_values")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_cols": feature_cols, "target_cols": TARGET_COLUMNS}, MODEL_PATH)

    stats = {
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "r2_per_target": {t: float(r) for t, r in zip(TARGET_COLUMNS, r2)},
        "mae_per_target": {t: float(m) for t, m in zip(TARGET_COLUMNS, mae)},
        "feature_columns": feature_cols,
    }
    with open(MODELS_DIR / "train_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print("Saved model to", MODEL_PATH)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()

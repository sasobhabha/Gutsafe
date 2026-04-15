"""Train a small neural net: additive presence -> microbiome impact vector."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import LABELS_CSV, MODELS_DIR, PRODUCTS_CSV, TARGET_COLUMNS


def feature_columns_from_products() -> list[str]:
    prod = pd.read_csv(PRODUCTS_CSV)
    excluded = {"product_id", "product_name"}
    cols = [c for c in prod.columns if c not in excluded]
    return [str(c).strip().lower() for c in cols]


def build_model(in_dim: int, out_dim: int, hidden_sizes: list[int]) -> nn.Module:
    layers: list[nn.Module] = []
    prev = in_dim
    for h in hidden_sizes:
        layers.append(nn.Linear(prev, h))
        layers.append(nn.ReLU())
        prev = h
    layers.append(nn.Linear(prev, out_dim))
    return nn.Sequential(*layers)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=600)
    parser.add_argument("--lr", type=float, default=2e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--hidden", type=str, default="64,32")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--out", type=str, default="microbiome_effect_nn.pt")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    hidden_sizes = [int(x) for x in args.hidden.split(",") if x.strip()]

    feature_cols = feature_columns_from_products()
    prod = pd.read_csv(PRODUCTS_CSV)
    labels = pd.read_csv(LABELS_CSV)
    df = prod.merge(labels, on="product_id", suffixes=("", "_y"))
    if "product_name_y" in df.columns:
        df.drop(columns=["product_name_y"], inplace=True)

    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing feature columns in merged table: {missing}")

    X = df[feature_cols].astype(np.float32).to_numpy()
    Y = df[TARGET_COLUMNS].astype(np.float32).to_numpy()

    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=args.test_size, random_state=args.seed
    )

    x_mean = X_train.mean(axis=0)
    x_std = X_train.std(axis=0)
    x_std[x_std < 1e-8] = 1.0
    y_mean = Y_train.mean(axis=0)
    y_std = Y_train.std(axis=0)
    y_std[y_std < 1e-8] = 1.0

    Xtr = (X_train - x_mean) / x_std
    Xte = (X_test - x_mean) / x_std
    Ytr = (Y_train - y_mean) / y_std
    Yte = (Y_test - y_mean) / y_std

    device = torch.device("cpu")
    model = build_model(len(feature_cols), len(TARGET_COLUMNS), hidden_sizes).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    loss_fn = nn.MSELoss()

    Xtr_t = torch.from_numpy(Xtr)
    Ytr_t = torch.from_numpy(Ytr)

    bs = max(4, int(args.batch_size))
    n = Xtr_t.shape[0]

    model.train()
    for _ in range(int(args.epochs)):
        idx = torch.randperm(n)
        for i in range(0, n, bs):
            b = idx[i : i + bs]
            pred = model(Xtr_t[b])
            loss = loss_fn(pred, Ytr_t[b])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        pred_te_norm = model(torch.from_numpy(Xte)).numpy()
    pred_te = pred_te_norm * y_std + y_mean

    r2 = r2_score(Y_test, pred_te, multioutput="raw_values")
    mae = mean_absolute_error(Y_test, pred_te, multioutput="raw_values")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = MODELS_DIR / args.out
    torch.save(
        {
            "feature_cols": feature_cols,
            "target_cols": TARGET_COLUMNS,
            "x_mean": x_mean.astype(np.float32),
            "x_std": x_std.astype(np.float32),
            "y_mean": y_mean.astype(np.float32),
            "y_std": y_std.astype(np.float32),
            "hidden_sizes": hidden_sizes,
            "state_dict": model.state_dict(),
        },
        str(out_path),
    )

    stats = {
        "model": "pytorch_mlp",
        "out_path": str(out_path),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "r2_per_target": {t: float(v) for t, v in zip(TARGET_COLUMNS, r2)},
        "mae_per_target": {t: float(v) for t, v in zip(TARGET_COLUMNS, mae)},
        "feature_columns": feature_cols,
        "hidden_sizes": hidden_sizes,
    }
    with open(MODELS_DIR / "train_stats_nn.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print("Saved NN bundle to", out_path)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()


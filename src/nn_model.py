"""Tiny PyTorch MLP used for microbiome effect prediction.

This is intentionally small and dependency-light: a multi-output regressor trained on
additive-presence features. It saves a self-contained bundle to disk so API inference
doesn't need scikit-learn objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class NNPredictBundle:
    feature_cols: list[str]
    target_cols: list[str]
    x_mean: np.ndarray
    x_std: np.ndarray
    y_mean: np.ndarray
    y_std: np.ndarray
    state_dict: dict[str, Any]
    hidden_sizes: list[int]


def _safe_std(std: np.ndarray) -> np.ndarray:
    std = std.astype(np.float32, copy=False)
    std[std < 1e-8] = 1.0
    return std


def load_nn_bundle(path: Path) -> NNPredictBundle:
    import torch

    # PyTorch >= 2.6 defaults `weights_only=True` which rejects numpy payloads.
    # This bundle is produced locally by our training script, so we load fully.
    try:
        obj = torch.load(str(path), map_location="cpu", weights_only=False)
    except TypeError:
        obj = torch.load(str(path), map_location="cpu")
    return NNPredictBundle(
        feature_cols=list(obj["feature_cols"]),
        target_cols=list(obj["target_cols"]),
        x_mean=np.asarray(obj["x_mean"], dtype=np.float32),
        x_std=_safe_std(np.asarray(obj["x_std"], dtype=np.float32)),
        y_mean=np.asarray(obj["y_mean"], dtype=np.float32),
        y_std=_safe_std(np.asarray(obj["y_std"], dtype=np.float32)),
        state_dict=dict(obj["state_dict"]),
        hidden_sizes=list(obj.get("hidden_sizes", [64, 32])),
    )


def predict_nn(bundle: NNPredictBundle, flags: dict[str, int]) -> dict[str, float]:
    """Predict per-target effects from additive flags using the NN bundle."""
    import torch
    import torch.nn as nn

    in_dim = len(bundle.feature_cols)
    out_dim = len(bundle.target_cols)

    layers: list[nn.Module] = []
    prev = in_dim
    for h in bundle.hidden_sizes:
        layers.append(nn.Linear(prev, h))
        layers.append(nn.ReLU())
        prev = h
    layers.append(nn.Linear(prev, out_dim))
    model = nn.Sequential(*layers)
    model.load_state_dict(bundle.state_dict)
    model.eval()

    x = np.asarray([float(flags.get(c, 0)) for c in bundle.feature_cols], dtype=np.float32)
    x = (x - bundle.x_mean) / bundle.x_std
    with torch.no_grad():
        y_norm = model(torch.from_numpy(x).unsqueeze(0)).squeeze(0).numpy()
    y = y_norm * bundle.y_std + bundle.y_mean
    return {t: float(v) for t, v in zip(bundle.target_cols, y.tolist())}


"""Shared scoring logic for CLI and HTTP API.

Combines (1) curated additive/chemical rows from data/additives_effects.csv matched in full text,
(2) common food-ingredient rows from data/ingredient_lexicon.csv matched per comma-separated segment,
plus a small ultra-processed proxy from ingredient-list length. Gut health 0–100 is never a flat
74 when real ingredient text is present — it always reflects the merged rubric.
"""

from __future__ import annotations

from typing import Any

import joblib
import pandas as pd

from config import ADDITIVES_CSV, MODEL_PATH, TARGET_COLUMNS
from ingredient_match import detect_additives
from lexicon_score import aggregate_lexicon_effects, merge_additive_and_lexicon

# Only when there is no ingredient text AND no scorable additive signal (e.g. empty API label).
BASELINE_NO_SIGNAL = 74.0
STRESS_SATURATION = 1.52


def deterministic_score(flags: dict[str, int]) -> dict[str, float]:
    add = pd.read_csv(ADDITIVES_CSV)
    add["col_name"] = add["additive"].str.strip().str.lower()
    out = {t: 0.0 for t in TARGET_COLUMNS}
    for _, a in add.iterrows():
        col = a["col_name"]
        if flags.get(col) != 1:
            continue
        for t in TARGET_COLUMNS:
            out[t] += float(a[t])
    return out


def compute_microbiome_stress(effects: dict[str, float]) -> float:
    b = effects["bifido_delta"]
    l = effects["lacto_delta"]
    ak = effects["akkermansia_delta"]
    ent = effects["enterobacteriaceae_delta"]
    div = effects["diversity_delta"]
    scfa = effects["scfa_delta"]
    bar = effects["barrier_risk"]

    beneficial_loss = abs(min(0.0, b)) + abs(min(0.0, l)) + abs(min(0.0, ak))
    opportunist = max(0.0, ent)
    eco_loss = abs(min(0.0, div)) + abs(min(0.0, scfa))
    barrier = max(0.0, min(1.2, bar))

    stress = (
        0.26 * beneficial_loss
        + 0.17 * opportunist
        + 0.17 * eco_loss
        + 0.40 * barrier
    )
    return max(0.0, stress)


def gut_health_score_0_100(
    effects: dict[str, float],
    has_ingredient_text: bool,
) -> tuple[float, float]:
    """
    If there is no ingredient paragraph AND no microbiome signal in effects → baseline.
    Otherwise: norm = stress / saturation in [0, 1], then health = (1 - norm) * 100.
    """
    stress_raw = compute_microbiome_stress(effects)
    if not has_ingredient_text and stress_raw < 1e-9:
        return BASELINE_NO_SIGNAL, 0.0

    norm = min(1.0, stress_raw / STRESS_SATURATION)
    health = (1.0 - norm) * 100.0
    health = max(0.0, min(100.0, health))
    return round(health, 2), round(norm, 4)


def all_additive_keys() -> list[str]:
    add = pd.read_csv(ADDITIVES_CSV)
    return [str(x).strip().lower() for x in add["additive"].tolist()]


def score_from_flags(flags: dict[str, int], use_model: bool = True) -> dict[str, Any]:
    """CLI / tests with explicit flags only (no full ingredient paragraph → no lexicon)."""
    for k in all_additive_keys():
        flags.setdefault(k, 0)
    lit_add = deterministic_score(flags)
    merged = merge_additive_and_lexicon(lit_add, {t: 0.0 for t in TARGET_COLUMNS}, 0)
    health, stress_norm = gut_health_score_0_100(merged, has_ingredient_text=False)

    result: dict[str, Any] = {
        "additive_flags": flags,
        "literature_aggregated_effects": merged,
        "lexicon_contribution": {t: 0.0 for t in TARGET_COLUMNS},
        "ingredient_segment_count": 0,
        "lexicon_keyword_hits": [],
        "microbiome_stress_index_0_1": stress_norm,
        "score_basis": (
            "additive_flags_only"
            if not any(int(flags.get(k, 0)) == 1 for k in all_additive_keys())
            else "additive_flags_literature"
        ),
        "wellbeing_index_0_100": health,
    }
    if use_model and MODEL_PATH.exists():
        bundle = joblib.load(MODEL_PATH)
        model = bundle["model"]
        feature_cols = list(bundle["feature_cols"])
        row = [float(flags.get(c, 0)) for c in feature_cols]
        X = pd.DataFrame([row], columns=feature_cols)
        pred = model.predict(X)[0]
        pred_effects = dict(zip(TARGET_COLUMNS, pred))
        result["model_predicted_effects"] = {t: float(v) for t, v in zip(TARGET_COLUMNS, pred)}
        m_health, m_stress = gut_health_score_0_100(pred_effects, has_ingredient_text=False)
        result["model_microbiome_stress_index_0_1"] = m_stress
        result["model_wellbeing_index_0_100"] = m_health
    else:
        result["model_wellbeing_index_0_100"] = result["wellbeing_index_0_100"]
    return result


def score_from_ingredients(ingredients_text: str | None, use_model: bool = True) -> dict[str, Any]:
    flags = detect_additives(ingredients_text)
    lit_add = deterministic_score(flags)
    lex_effects, n_seg, lex_matched = aggregate_lexicon_effects(ingredients_text)
    merged = merge_additive_and_lexicon(lit_add, lex_effects, n_seg)
    has_text = bool((ingredients_text or "").strip())
    health, stress_norm = gut_health_score_0_100(merged, has_text)

    basis = "full_ingredients_additives_lexicon"
    if not has_text:
        basis = "no_ingredient_text"

    result: dict[str, Any] = {
        "additive_flags": flags,
        "literature_aggregated_effects": merged,
        "additive_only_effects": lit_add,
        "lexicon_contribution": lex_effects,
        "ingredient_segment_count": n_seg,
        "lexicon_keyword_hits": lex_matched[:40],
        "microbiome_stress_index_0_1": stress_norm,
        "score_basis": basis,
        "wellbeing_index_0_100": health,
    }

    if use_model and MODEL_PATH.exists():
        bundle = joblib.load(MODEL_PATH)
        model = bundle["model"]
        feature_cols = list(bundle["feature_cols"])
        row = [float(flags.get(c, 0)) for c in feature_cols]
        X = pd.DataFrame([row], columns=feature_cols)
        pred = model.predict(X)[0]
        pred_add = dict(zip(TARGET_COLUMNS, pred))
        result["model_predicted_effects"] = {t: float(v) for t, v in zip(TARGET_COLUMNS, pred)}
        merged_model = merge_additive_and_lexicon(pred_add, lex_effects, n_seg)
        m_health, m_stress = gut_health_score_0_100(merged_model, has_text)
        result["model_effects_with_lexicon"] = merged_model
        result["model_microbiome_stress_index_0_1"] = m_stress
        result["model_wellbeing_index_0_100"] = m_health
    else:
        result["model_wellbeing_index_0_100"] = result["wellbeing_index_0_100"]

    return result


def additives_with_citations() -> list[dict[str, Any]]:
    df = pd.read_csv(ADDITIVES_CSV)
    rows = []
    for _, r in df.iterrows():
        row = {"additive": r["additive"], "citation": r.get("citation", "")}
        for t in TARGET_COLUMNS:
            row[t] = float(r[t])
        rows.append(row)
    return rows

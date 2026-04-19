"""HTTP API + static site: barcode lookup (OFF + USDA FDC + optional SmartLabel) + GutSafety scoring."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent
_WEB = _ROOT / "web"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from product_sources import (
    fetch_open_food_facts,
    fetch_smartlabel_label_insight,
    fetch_usda_fdc_branded,
    fetch_walmart_product,
    fetch_target_product,
    fetch_kroger_product,
    merge_product,
    smartlabel_configured,
    UpstreamRateLimited,
)
from scoring import score_from_ingredients

app = FastAPI(title="GutSafety AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalize_barcode(barcode: str) -> str:
    digits = re.sub(r"\D", "", barcode or "")
    if len(digits) < 8:
        raise HTTPException(
            status_code=400, detail="Barcode must contain at least 8 digits."
        )
    if len(digits) > 14:
        digits = digits[-14:]
    return digits


@app.get("/api/health")
def health() -> dict:
    has_usda = True
    return {
        "ok": True,
        "service": "gutsafety",
        "ingredient_sources": [
            "open_food_facts",
            "usda_fdc_branded",
            "smartlabel_label_insight_optional",
        ],
        "usda_fdc_api_key_configured": has_usda,
        "smartlabel_label_insight_configured": smartlabel_configured(),
        "usda_note": "USDA key is embedded in code (env override disabled).",
        "smartlabel_note": "Set SMARTLABEL_API_KEY + SMARTLABEL_CONFIGURATION_ID (Label Insight / SmartLabel).",
    }


@app.get("/api/scan/{barcode}")
def scan_barcode(
    barcode: str,
    use_model: bool = True,
    use_usda: bool = True,
    use_smartlabel: bool = True,
) -> dict:
    code = normalize_barcode(barcode)

    off = None
    off_err: str | None = None
    try:
        off = fetch_open_food_facts(code)
    except UpstreamRateLimited as e:
        off_err = str(e)
    except requests.RequestException as e:
        off_err = str(e)

    usda = None
    usda_err: str | None = None
    if use_usda:
        try:
            usda = fetch_usda_fdc_branded(code, None)
        except UpstreamRateLimited as e:
            usda_err = str(e)
        except requests.RequestException as e:
            usda_err = str(e)

    sl = None
    sl_err: str | None = None
    if use_smartlabel and smartlabel_configured():
        try:
            sl = fetch_smartlabel_label_insight(code)
        except requests.RequestException as e:
            sl_err = str(e)

    # Fallback: supermarket scrapers if OFF and USDA fail
    walmart = None
    target = None
    kroger = None
    if off is None and usda is None:
        try:
            walmart = fetch_walmart_product(code)
        except Exception:
            pass
        if walmart and walmart.get("ingredients_text"):
            off = walmart  # Use as primary fallback
        else:
            try:
                target = fetch_target_product(code)
            except Exception:
                pass
            if target and target.get("ingredients_text"):
                off = target
            else:
                try:
                    kroger = fetch_kroger_product(code)
                except Exception:
                    pass
                if kroger and kroger.get("ingredients_text"):
                    off = kroger

    # If upstreams are rate-limiting or unreachable, return a temporary error instead of "not found".
    off_msg = (off_err or "").lower()
    usda_msg = (usda_err or "").lower()
    upstream_temp = (
        ("rate limited" in off_msg)
        or ("rate limited" in usda_msg)
        or ("429" in usda_msg)
        or ("connection refused" in off_msg)
        or ("failed to establish a new connection" in off_msg)
        or ("name or service not known" in off_msg)
        or ("temporary failure in name resolution" in off_msg)
        or ("timed out" in off_msg)
    )
    if upstream_temp and off is None and usda is None and sl is None:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Upstream ingredient databases are temporarily unavailable (network/rate limit).",
                "open_food_facts": off_err,
                "usda_fdc": usda_err,
                "smartlabel": "not configured"
                if not smartlabel_configured()
                else sl_err,
                "fix": "Set USDA_FDC_API_KEY on the API host to avoid DEMO_KEY limits; retry in a minute; or disable USDA with use_usda=false.",
            },
        )

    if off is None and usda is None and sl is None:
        raise HTTPException(status_code=404, detail="Product not found")

    merged = merge_product(code, off, usda, sl)
    ing = merged.get("ingredients_text") or ""
    if not ing.strip():
        raise HTTPException(status_code=404, detail="Product not found")
    warning_parts = list(merged.get("warnings") or [])
    if merged.get("smartlabel_allergen_advisory"):
        warning_parts.append("Advisory: " + merged["smartlabel_allergen_advisory"])
    warning = " | ".join(warning_parts) if warning_parts else None

    score = score_from_ingredients(ing if ing.strip() else None, use_model=use_model)

    return {
        "barcode": merged["barcode"],
        "sources": merged["sources"],
        "product_name": merged["product_name"],
        "brands": merged["brands"],
        "category": merged.get("category") or "",
        "image_url": merged["image_url"],
        "ingredients_text": ing,
        "ingredients_by_source": merged.get("ingredients_by_source"),
        "usda_fdc_id": merged.get("usda_fdc_id"),
        "usda_gtin_upc": merged.get("usda_gtin_upc"),
        "smartlabel_upc": merged.get("smartlabel_upc"),
        "source_errors": {
            "open_food_facts": off_err,
            "usda_fdc": usda_err,
            "smartlabel": sl_err,
        },
        "warning": warning,
        "score": score,
    }


@app.get("/")
def index() -> FileResponse:
    index_path = _WEB / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=500, detail="web/index.html missing")
    return FileResponse(index_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

"""
Multi-source product lookup for barcode → ingredients.

- Open Food Facts: global, crowdsourced (https://openfoodfacts.github.io/openfoodfacts-server/api/)
- USDA FoodData Central: Global Branded Foods / SR Legacy API (https://fdc.nal.usda.gov/api-guide.html)
  Use a free API key: set USDA_FDC_API_KEY in the environment (DEMO_KEY works for light testing).
- SmartLabel® (Label Insight Products API): digital disclosure data served by Label Insight for participating
  brands (https://www.smartlabel.org/). UPC lookup:
  GET https://api.labelinsight.com/products/v1/{configurationId}/upc/{upc}
  Requires SMARTLABEL_API_KEY + SMARTLABEL_CONFIGURATION_ID from Label Insight / SmartLabel onboarding
  (https://developers.labelinsight.com/reference/get-product-by-upc-resource).
"""

from __future__ import annotations

import os
import re
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

OFF_PRODUCT_V0 = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
# Newer OFF API (recommended). Uses .net domain for API traffic.
# Docs: https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/
OFF_PRODUCT_V2 = "https://world.openfoodfacts.net/api/v2/product/{barcode}"
OFF_HEADERS = {
    "User-Agent": "GutSafetyAI/1.0 (Open Food Facts; ingredient lookup)",
    "Accept": "application/json",
}

# Fallback: Walmart product page scraper (no API key needed)
Walmart_PRODUCT = "https://www.walmart.com/ip/{barcode}"
# Fallback: Target product page scraper
Target_PRODUCT = "https://www.target.com/p/{barcode}"
# Fallback: Kroger product page
Kroger_PRODUCT = "https://www.kroger.com/p/{barcode}"

FDC_SEARCH = "https://api.nal.usda.gov/fdc/v1/foods/search"
FDC_FOOD = "https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"

# Dummy fallback key (replace later). Prefer setting USDA_FDC_API_KEY in env.
DEFAULT_USDA_FDC_API_KEY = "x65puQKmMmVBnHKE2CZ8CPWDpsgevJwxQP9DzsMK"

# SmartLabel / Label Insight — Products API v1 (ingredients.declaration)
LABEL_INSIGHT_PRODUCT = (
    "https://api.labelinsight.com/products/v1/{configuration_id}/upc/{upc}"
)


class UpstreamRateLimited(Exception):
    """Raised when an upstream datasource rate-limits (HTTP 429)."""


def _session() -> requests.Session:
    """
    Requests session with conservative retries for transient network errors.
    (Not used to bypass rate limits; 429 is handled explicitly.)
    """
    s = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _core_barcode(d: str) -> str:
    d = _digits(d)
    c = d.lstrip("0")
    return c if c else "0"


def barcode_matches(candidate_gtin: str | None, requested_barcode: str) -> bool:
    """Loose GTIN match (handles 12-digit UPC vs 13-digit EAN padding)."""
    if not candidate_gtin:
        return False
    a = _core_barcode(candidate_gtin)
    b = _core_barcode(requested_barcode)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 8 and len(b) >= 8 and (a.endswith(b) or b.endswith(a)):
        return True
    return False


def fetch_open_food_facts(barcode: str) -> dict[str, Any] | None:
    s = _session()

    # Try API v2 first (often more reliable and smaller payload with fields=).
    v2_url = OFF_PRODUCT_V2.format(barcode=barcode)
    v2_params = {
        "fields": "product_name,product_name_en,brands,ingredients_text,ingredients_text_en,image_front_url,image_front_small_url",
    }
    r = s.get(v2_url, params=v2_params, timeout=20, headers=OFF_HEADERS)
    if r.status_code == 429:
        raise UpstreamRateLimited(
            "Open Food Facts rate limited (HTTP 429). Try again later."
        )
    if r.status_code == 404:
        return None
    if r.ok:
        payload = r.json()
        p = payload.get("product") or payload
        # v2 returns { product: {...} } or sometimes the product object directly depending on proxy/cache layers
        if not isinstance(p, dict) or not p:
            return None
        return {
            "source": "open_food_facts",
            "product_name": p.get("product_name") or p.get("product_name_en") or "",
            "brands": p.get("brands") or "",
            "ingredients_text": (
                p.get("ingredients_text") or p.get("ingredients_text_en") or ""
            ).strip(),
            "image_url": p.get("image_front_url")
            or p.get("image_front_small_url")
            or "",
            "raw": p,
        }

    # Fallback: legacy v0 endpoint
    url = OFF_PRODUCT_V0.format(barcode=barcode)
    r0 = s.get(url, timeout=20, headers=OFF_HEADERS)
    if r0.status_code == 429:
        raise UpstreamRateLimited(
            "Open Food Facts rate limited (HTTP 429). Try again later."
        )
    r0.raise_for_status()
    payload0 = r0.json()
    if payload0.get("status") != 1 or not payload0.get("product"):
        return None
    p0 = payload0["product"]
    return {
        "source": "open_food_facts",
        "product_name": p0.get("product_name") or p0.get("product_name_en") or "",
        "brands": p0.get("brands") or "",
        "ingredients_text": (
            p0.get("ingredients_text") or p0.get("ingredients_text_en") or ""
        ).strip(),
        "image_url": p0.get("image_front_url") or p0.get("image_front_small_url") or "",
        "raw": p0,
    }


def _fdc_api_key() -> str | None:
    # Intentionally *do not* read from environment: per product requirement,
    # the embedded dummy key is the only key used by the app.
    return DEFAULT_USDA_FDC_API_KEY


def _smartlabel_credentials() -> tuple[str | None, str | None]:
    key = (
        os.environ.get("SMARTLABEL_API_KEY")
        or os.environ.get("LABEL_INSIGHT_API_KEY")
        or ""
    ).strip() or None
    cid = (
        os.environ.get("SMARTLABEL_CONFIGURATION_ID")
        or os.environ.get("LABEL_INSIGHT_CONFIGURATION_ID")
        or ""
    ).strip() or None
    return key, cid


def smartlabel_configured() -> bool:
    k, c = _smartlabel_credentials()
    return bool(k and c)


def fetch_smartlabel_label_insight(barcode: str) -> dict[str, Any] | None:
    """
    Label Insight Products API — powers SmartLabel® digital pages for many CPG brands.
    Returns None if credentials unset, product not found (404), or forbidden (403).
    """
    key, cid = _smartlabel_credentials()
    if not key or not cid:
        return None
    url = LABEL_INSIGHT_PRODUCT.format(configuration_id=cid, upc=barcode)
    r = requests.get(
        url,
        timeout=25,
        headers={
            "X-API-KEY": key,
            "Accept": "application/json",
            "User-Agent": "GutSafetyAI/1.0 (SmartLabel/Label Insight product lookup)",
        },
    )
    if r.status_code in (403, 404):
        return None
    r.raise_for_status()
    data = r.json()
    ing = data.get("ingredients") or {}
    decl = (ing.get("declaration") or "").strip()
    symbols = ing.get("symbols") or []
    footnotes: list[str] = []
    if isinstance(symbols, list):
        footnotes = [str(s).strip() for s in symbols if s]
    full = decl
    if footnotes:
        full = (
            (decl + "\n\n" + "\n".join(footnotes)).strip()
            if decl
            else "\n".join(footnotes)
        )

    cat = ""
    cg = data.get("categorization")
    if isinstance(cg, dict):
        cat = (cg.get("category") or cg.get("shelf") or "").strip()

    return {
        "source": "smartlabel",
        "product_name": (data.get("productTitle") or "").strip(),
        "brands": (data.get("brand") or "").strip(),
        "sub_brand": (data.get("subBrand") or "").strip(),
        "category": cat,
        "ingredients_text": full,
        "allergen_advisory": (data.get("warning") or "").strip(),
        "upc": (data.get("upc") or "").strip(),
        "image_url": "",
        "raw": data,
    }


def fetch_usda_fdc_branded(barcode: str, api_key: str | None) -> dict[str, Any] | None:
    """
    Search Branded foods by GTIN-like query, then fetch full food record for ingredient text.
    """
    key = api_key or _fdc_api_key() or "DEMO_KEY"
    params = {"api_key": key}
    body = {
        "query": barcode,
        "pageSize": 15,
        "dataType": ["Branded"],
    }
    r = _session().post(FDC_SEARCH, params=params, json=body, timeout=25)
    if r.status_code == 429:
        raise UpstreamRateLimited(
            "USDA FoodData Central rate limited (HTTP 429). Use a real USDA_FDC_API_KEY (not DEMO_KEY) or retry later."
        )
    r.raise_for_status()
    data = r.json()
    foods = data.get("foods") or []
    hit: dict[str, Any] | None = None
    for f in foods:
        if barcode_matches(f.get("gtinUpc"), barcode):
            hit = f
            break
    if hit is None:
        return None

    fdc_id = hit.get("fdcId")
    if not fdc_id:
        return None

    fr = _session().get(
        FDC_FOOD.format(fdc_id=fdc_id), params={"api_key": key}, timeout=25
    )
    if fr.status_code == 429:
        raise UpstreamRateLimited(
            "USDA FoodData Central rate limited (HTTP 429) on details request. Use a real USDA_FDC_API_KEY or retry later."
        )
    fr.raise_for_status()
    detail = fr.json()
    ing = (detail.get("ingredients") or "").strip()
    name = detail.get("description") or hit.get("description") or ""
    brand = detail.get("brandOwner") or detail.get("brandName") or ""
    cats = detail.get("foodCategory") or {}
    cat_label = ""
    if isinstance(cats, dict):
        cat_label = cats.get("label") or ""

    return {
        "source": "usda_fdc",
        "fdc_id": fdc_id,
        "product_name": name,
        "brands": brand,
        "category": cat_label,
        "ingredients_text": ing,
        "gtin_upc": (hit.get("gtinUpc") or "").strip(),
        "image_url": "",
        "raw": detail,
    }


def _pick_ingredients(
    off: dict[str, Any] | None,
    usda: dict[str, Any] | None,
    smartlabel: dict[str, Any] | None,
) -> tuple[str, str | None]:
    """
    Choose best ingredient string: prefer longest non-empty; break ties SmartLabel > USDA > OFF.
    Returns (chosen_text, secondary_note).
    """
    candidates: list[tuple[str, str]] = []
    for label, d in (
        ("open_food_facts", off),
        ("usda_fdc", usda),
        ("smartlabel", smartlabel),
    ):
        if not d:
            continue
        t = (d.get("ingredients_text") or "").strip()
        if t:
            candidates.append((t, label))
    if not candidates:
        return "", None

    priority = {"smartlabel": 0, "usda_fdc": 1, "open_food_facts": 2}
    best = max(candidates, key=lambda x: (len(x[0]), -priority.get(x[1], 9)))
    chosen_text, src = best
    note: str | None = None
    if len(candidates) > 1:
        longest = max(len(c[0]) for c in candidates)
        winners = [c for c in candidates if len(c[0]) == longest]
        if len(winners) == 1:
            wsrc = winners[0][1]
            pretty = wsrc.replace("_", " ")
            note = f"{pretty} ingredient list was longest; used for scoring."
        elif len(winners) > 1:
            pretty = src.replace("_", " ")
            note = f"Tied length across sources; preferred {pretty} (SmartLabel > USDA > Open Food Facts)."
    return chosen_text, note


def merge_product(
    barcode: str,
    off: dict[str, Any] | None,
    usda: dict[str, Any] | None,
    smartlabel: dict[str, Any] | None,
) -> dict[str, Any]:
    sources: list[str] = []
    if off:
        sources.append("open_food_facts")
    if usda:
        sources.append("usda_fdc")
    if smartlabel:
        sources.append("smartlabel")

    ing, ing_note = _pick_ingredients(off, usda, smartlabel)

    name = ""
    brands = ""
    image = ""
    if off:
        name = off.get("product_name") or name
        brands = off.get("brands") or brands
        image = off.get("image_url") or image
    if usda:
        if not name:
            name = usda.get("product_name") or ""
        if not brands:
            brands = usda.get("brands") or ""
    if smartlabel:
        if not name:
            name = smartlabel.get("product_name") or ""
        if not brands:
            brands = smartlabel.get("brands") or ""

    warnings: list[str] = []
    if not ing.strip():
        warnings.append("Product not found")

    category = (usda or {}).get("category") or ""
    if smartlabel and (smartlabel.get("category") or "").strip():
        if category:
            category = f"{category}; {smartlabel['category']}"
        else:
            category = (smartlabel.get("category") or "").strip()

    adv: list[str] = []
    if smartlabel and (smartlabel.get("allergen_advisory") or "").strip():
        adv.append(smartlabel["allergen_advisory"])

    return {
        "barcode": barcode,
        "sources": sources,
        "product_name": name or "Unknown product",
        "brands": brands or "",
        "category": category,
        "image_url": image,
        "ingredients_text": ing,
        "ingredients_by_source": {
            "open_food_facts": (off or {}).get("ingredients_text") or "",
            "usda_fdc": (usda or {}).get("ingredients_text") or "",
            "smartlabel": (smartlabel or {}).get("ingredients_text") or "",
        },
        "usda_fdc_id": (usda or {}).get("fdc_id"),
        "usda_gtin_upc": (usda or {}).get("gtin_upc"),
        "smartlabel_upc": (smartlabel or {}).get("upc"),
        "smartlabel_allergen_advisory": " ".join(adv) if adv else "",
        "warnings": warnings,
    }


def fetch_walmart_product(barcode: str) -> dict[str, Any] | None:
    """Scrape Walmart product page for ingredients (fallback when OFF/USDA fail)."""
    import re
    from bs4 import BeautifulSoup

    s = _session()
    url = f"https://www.walmart.com/ip/{barcode}"
    try:
        r = s.get(url, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        product_name = None
        ingredients = None
        brand = None
        # Try to find product name
        title = soup.find("h1", {"itemprop": "name"}) or soup.find("h1")
        if title:
            product_name = title.get_text(strip=True)
        # Find ingredients - Walmart uses JSON-LD script
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if data.get("@type") == "Product":
                        product_name = product_name or data.get("name")
                        recipe = data.get("recipeIngredient") or data.get("ingredients")
                        if recipe:
                            ingredients = (
                                ", ".join(recipe)
                                if isinstance(recipe, list)
                                else recipe
                            )
                        break
                    elif isinstance(data, list):
                        for item in data:
                            if item.get("@type") == "Product":
                                product_name = product_name or item.get("name")
                                recipe = item.get("recipeIngredient") or item.get(
                                    "ingredients"
                                )
                                if recipe:
                                    ingredients = (
                                        ", ".join(recipe)
                                        if isinstance(recipe, list)
                                        else recipe
                                    )
                                break
            except Exception:
                pass
        # Fallback: look for ingredients in div/data attributes
        if not ingredients:
            ing_div = soup.find("div", {"data-testid": "product-ingredients"})
            if ing_div:
                ingredients = ing_div.get_text(strip=True)
        if not product_name:
            return None
        return {
            "product_name": product_name,
            "brands": brand or "",
            "ingredients_text": ingredients or "",
            "image_url": "",
        }
    except Exception:
        return None


def fetch_target_product(barcode: str) -> dict[str, Any] | None:
    """Scrape Target product page for ingredients (fallback when OFF/USDA fail)."""
    from bs4 import BeautifulSoup

    s = _session()
    # Target uses UPC in path, may need to find product slug
    url = f"https://www.target.com/p/{barcode}"
    try:
        r = s.get(url, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        # Target has JSON-LD too
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    return {
                        "product_name": data.get("name", ""),
                        "brands": "",
                        "ingredients_text": ", ".join(data.get("recipeIngredient", []))
                        if data.get("recipeIngredient")
                        else "",
                        "image_url": data.get("image", [{}])[0].get("url", "")
                        if data.get("image")
                        else "",
                    }
            except Exception:
                pass
        return None
    except Exception:
        return None


def fetch_kroger_product(barcode: str) -> dict[str, Any] | None:
    """Scrape Kroger product page for ingredients (fallback when OFF/USDA fail)."""
    from bs4 import BeautifulSoup

    s = _session()
    url = f"https://www.kroger.com/p/{barcode}"
    try:
        r = s.get(url, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        # Kroger has JSON-LD
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    return {
                        "product_name": data.get("name", ""),
                        "brands": data.get("brand", ""),
                        "ingredients_text": ", ".join(data.get("recipeIngredient", []))
                        if data.get("recipeIngredient")
                        else "",
                        "image_url": data.get("image", [{}])[0].get("url", "")
                        if data.get("image")
                        else "",
                    }
            except Exception:
                pass
        return None
    except Exception:
        return None


# Import json for fallback scrapers
import json

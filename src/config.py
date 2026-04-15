"""Paths and additive synonym lists for ingredient text matching."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
ADDITIVES_CSV = DATA_DIR / "additives_effects.csv"
PRODUCTS_CSV = DATA_DIR / "products_additives.csv"
LABELS_CSV = DATA_DIR / "products_microbiome_labels.csv"
MODEL_PATH = MODELS_DIR / "microbiome_effect_model.pkl"
NN_MODEL_PATH = MODELS_DIR / "microbiome_effect_nn.pt"

# column_name in CSV / model features -> phrases and E-numbers to search in ingredients_text
ADDITIVE_PATTERNS: dict[str, list[str]] = {
    "sucralose": ["sucralose", "e955"],
    "aspartame": ["aspartame", "e951"],
    "stevia": ["stevia", "rebaudioside", "steviol", "e960"],
    "polysorbate80": ["polysorbate 80", "polysorbate-80", "polysorbate80", "e433"],
    "polysorbate60": ["polysorbate 60", "polysorbate-60", "polysorbate60", "e435"],
    "cmc": [
        "carboxymethylcellulose",
        "carboxymethyl cellulose",
        "cellulose gum",
        " e466",
        "e466 ",
        "e466,",
        "e466)",
        "(e466",
    ],
    "red40": ["red 40", "red40", "allura red", "allura red ac", "e129"],
    "carrageenan": ["carrageenan", "carrageen", "e407", "e407a"],
    "titanium_dioxide": [
        "titanium dioxide",
        "tio2",
        "e171",
    ],
    "msg": [
        "monosodium glutamate",
        "monosodium l-glutamate",
        "msg",
        "e621",
    ],
    "potassium_sorbate": ["potassium sorbate", "e202"],
    "sodium_benzoate": ["sodium benzoate", "e211"],
    "sodium_nitrite": [
        "sodium nitrite",
        "sodium nitrate",
        "potassium nitrite",
        "potassium nitrate",
        "e250",
        "e251",
        "e252",
    ],
    "phosphoric_acid": ["phosphoric acid", "e338"],
    "citric_acid": ["citric acid", "e330"],
    "xylitol": ["xylitol", "e967"],
    "sorbitol": ["sorbitol", "e420"],
    "maltitol": ["maltitol", "e965"],
    "tartrazine": ["tartrazine", "yellow 5", "yellow no. 5", "yellow no 5", "e102"],
    "saccharin": ["saccharin", "saccharine", "e954"],
    "acesulfame_k": ["acesulfame k", "acesulfame potassium", "ace-k", "ace k", "e950"],
    "guar_gum": ["guar gum", "e412"],
    "xanthan_gum": ["xanthan gum", "e415"],
    "propylene_glycol": ["propylene glycol", "e1520"],
}

TARGET_COLUMNS = [
    "bifido_delta",
    "lacto_delta",
    "akkermansia_delta",
    "enterobacteriaceae_delta",
    "diversity_delta",
    "scfa_delta",
    "barrier_risk",
]

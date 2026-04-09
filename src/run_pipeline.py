"""Fetch data (optional), build labels, train model."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import DATA_DIR, PRODUCTS_CSV


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample-only",
        action="store_true",
        help="Use data/sample_products_additives.csv instead of Open Food Facts.",
    )
    parser.add_argument("--pages", type=int, default=5)
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args()

    python = sys.executable

    if args.sample_only:
        src = DATA_DIR / "sample_products_additives.csv"
        shutil.copy(src, PRODUCTS_CSV)
        print(f"Copied {src} -> {PRODUCTS_CSV}", flush=True)
    else:
        run([python, str(_SRC / "build_product_matrix.py"), "--pages", str(args.pages)])

    run([python, str(_SRC / "build_training_table.py")])
    run([python, str(_SRC / "train_microbiome_model.py")])


if __name__ == "__main__":
    main()

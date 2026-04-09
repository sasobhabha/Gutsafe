"""Score a product from ingredient text or additive flags."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scoring import score_from_flags, score_from_ingredients


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingredients", type=str, default="", help="Raw ingredients label text.")
    parser.add_argument("--json-flags", type=str, default="", help='e.g. {"sucralose":1}')
    parser.add_argument("--use-model", action="store_true", help="Use trained forest if available.")
    args = parser.parse_args()

    if args.json_flags:
        flags = {k.lower(): int(v) for k, v in json.loads(args.json_flags).items()}
        result = score_from_flags(flags, use_model=args.use_model)
    else:
        result = score_from_ingredients(args.ingredients or None, use_model=args.use_model)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

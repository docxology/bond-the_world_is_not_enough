#!/usr/bin/env python3
"""ELEKTRA — render the four concept figures.

Thin orchestrator: bootstraps ``src/`` and calls
``the_world_is_not_enough.figures.generate_all_figures``, writing the four
PNGs under ``output/figures/`` by default (git-ignored, regenerable). Exits 0
iff all four figures are produced.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from the_world_is_not_enough.figures import generate_all_figures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=None,
        help="figure output directory (default: <root>/output/figures)",
    )
    args = parser.parse_args()
    output_dir = (
        Path(args.output_dir) if args.output_dir else ROOT / "output" / "figures"
    )
    figures = generate_all_figures(output_dir)
    for name, path in figures.items():
        print(f"{name} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

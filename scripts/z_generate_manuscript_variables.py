#!/usr/bin/env python3
"""ELEKTRA — hydrate manuscript ``{{TOKEN}}``s from config + measured model outputs.

Usage:
    uv run python scripts/z_generate_manuscript_variables.py [--allow-draft]

Strict by default: unresolved ``{{TOKEN}}``s in a manuscript section fail the
run. ``--allow-draft`` writes the resolved tree anyway (intentional early
drafts only). Writes ``output/data/manuscript_variables.json`` and the resolved
tree under ``output/manuscript/``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from the_world_is_not_enough.manuscript_variables import (
    generate_variables,
    resolve_manuscript_tree,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="write even if tokens remain unresolved",
    )
    parser.add_argument("--config", default=None, help="path to manuscript/config.yaml")
    parser.add_argument(
        "--manuscript-dir", default=None, help="manuscript source directory"
    )
    parser.add_argument(
        "--output-dir", default=None, help="output directory (default: <root>/output)"
    )
    args = parser.parse_args()

    variables = generate_variables(config_path=args.config)
    output_root = Path(args.output_dir) if args.output_dir else ROOT / "output"

    variables_path = output_root / "data" / "manuscript_variables.json"
    variables_path.parent.mkdir(parents=True, exist_ok=True)
    variables_path.write_text(
        json.dumps(variables, sort_keys=True, indent=2), encoding="utf-8"
    )

    resolve_manuscript_tree(
        variables,
        manuscript_dir=args.manuscript_dir,
        output_dir=output_root / "manuscript",
        strict=not args.allow_draft,
    )
    print(f"Resolved {len(variables)} manuscript variables -> {variables_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""ELEKTRA mission phase — recon.

Runs the reconnaissance stage against the ELEKTRA provider with a
deterministic goal string and prints the canonical ``ReconReport`` JSON.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bond_api.discovery import load_provider
from bond_api.protocol import ReconRequest
from bond_api.serialization import to_json

SLUG = "the_world_is_not_enough"
GOAL = "prepare the ELEKTRA mission across all three pillars"


def main() -> int:
    provider = load_provider(SLUG, search_paths=[str(SRC)])
    report = provider.recon(ReconRequest(goal=GOAL))
    print(to_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

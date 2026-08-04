#!/usr/bin/env python3
"""ELEKTRA mission phase — debrief.

Prints the ``Debrief`` (outcome + lessons) the ELEKTRA provider returns after
execution, as canonical BOND-API JSON.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bond_api.discovery import load_provider
from bond_api.serialization import to_json

SLUG = "the_world_is_not_enough"


def main() -> int:
    provider = load_provider(SLUG, search_paths=[str(SRC)])
    outcome = provider.execute(provider.plan(provider.brief()))
    print(to_json(provider.debrief(outcome)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

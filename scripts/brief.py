#!/usr/bin/env python3
"""ELEKTRA mission phase — brief.

Prints the frozen ``MissionBrief`` declared by the ELEKTRA provider as
canonical BOND-API JSON. Thin orchestrator: bootstraps ``src/`` onto
``sys.path``, loads the provider by slug through ``bond_api.discovery``, and
serializes the brief deterministically.
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
    print(to_json(provider.brief()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

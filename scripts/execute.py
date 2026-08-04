#!/usr/bin/env python3
"""ELEKTRA mission phase — execute.

Runs the full mission against the ELEKTRA provider and prints the canonical
``MissionOutcome`` JSON. Also persists a provenance-outcome record into
``output/data/`` through ``bond_utilities.mission_io.record_provenance_outcome``
(the shared Layer-0 provenance binding). Provenance is deterministic: the
mission epoch is a fixed nominal start, so the record is byte-reproducible.
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
from bond_utilities.mission_io import record_provenance_outcome

SLUG = "the_world_is_not_enough"
MISSION_EPOCH = "2026-08-04T00:00:00+00:00"  # fixed nominal mission clock


def main() -> int:
    provider = load_provider(SLUG, search_paths=[str(SRC)])
    plan = provider.plan(provider.brief())
    outcome = provider.execute(plan)
    print(to_json(outcome))

    record_path = ROOT / "output" / "data" / "elektra_mission.json"
    record = record_provenance_outcome(
        mission_id=SLUG,
        seed=outcome.provenance.seed,
        version=outcome.provenance.package_version,
        input_payload={"input_hash": outcome.provenance.input_hash},
        outcome=outcome.results,
        path=str(record_path),
        fmt="json",
        codename="ELEKTRA",
        started_at=MISSION_EPOCH,
    )
    print(
        f"provenance record -> {record_path} (seed {record['seed']})", file=sys.stderr
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

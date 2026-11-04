"""Manuscript ``{{TOKEN}}`` generation from ``manuscript/config.yaml``.

Tokens are computed, never hand-authored in prose: every value either comes
straight from the mission config or is derived deterministically from it by
the library modules (clock window math, codename sampling, cipher registry).

No token reads the wall clock. Every persisted artifact is a function of
committed inputs only, which is what makes regeneration byte-identical --
``tests/test_regeneration_determinism.py`` runs the documented regeneration
command twice, across a real second boundary, and requires the whole
``output/`` tree to hash the same both times.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .ciphers import CIPHER_DESCRIPTIONS, CIPHER_NAMES, CRYPTANALYSIS_HELPERS
from .clock import parse_schedule, windows_overlap
from .codenames import (
    ADJECTIVES,
    CODENAME_SCHEMES,
    NOUNS,
    codenames_by_scheme,
    generate_codenames,
    nato_codename,
)
from .randomness import SEEDED_HELPERS

#: Fallback quality-gate values when ``config.yaml`` omits a ``testing`` section.
DEFAULT_COVERAGE_GATE_PERCENT = 90
DEFAULT_MAX_TEST_FAILURES = 0

#: Manuscript config path, relative to the project root.
CONFIG_RELATIVE = Path("manuscript") / "config.yaml"


def load_mission_config(project_root: str | Path | None = None) -> dict[str, Any]:
    """Load and return the manuscript ``config.yaml`` contents.

    Args:
        project_root: Project root; defaults to the parent of ``src/``
            (i.e. the bond-utilities package root).

    Returns:
        The parsed config mapping.

    Raises:
        FileNotFoundError: If the config file is missing.
        ValueError: If the file does not contain a mapping.
    """
    root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[2]
    config_path = root / CONFIG_RELATIVE
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("config.yaml must contain a mapping")
    return config


def manuscript_instant(config: dict[str, Any]) -> datetime:
    """Return the committed reference instant for a manuscript render.

    This is the package's single source of "when", and it is deliberately
    **not** the wall clock: it is ``paper.date`` from ``config.yaml`` taken at
    midnight UTC, falling back to the mission schedule start when the config
    omits a paper date. Both are committed values, so two renders of the same
    commit pin the same instant and produce identical bytes.

    A ``paper.date`` that is present but unparseable raises rather than
    silently falling back — a malformed date must not degrade into a
    different, still-green answer.

    Args:
        config: Parsed ``manuscript/config.yaml`` mapping.

    Returns:
        The reference instant, timezone-aware in UTC.

    Raises:
        ValueError: If ``paper.date`` is present but is not an ISO-8601 date,
            or is absent with no usable ``mission.schedule`` to fall back to.
    """
    paper = config.get("paper")
    raw = paper.get("date") if isinstance(paper, dict) else None
    if raw is None:
        mission = config.get("mission")
        schedule = mission.get("schedule") if isinstance(mission, dict) else None
        if not isinstance(schedule, dict):
            raise ValueError("config.yaml needs paper.date or mission.schedule to fix the reference instant")
        return parse_schedule(schedule)[0]
    if isinstance(raw, datetime):
        return raw if raw.tzinfo is not None else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, date):
        return datetime(raw.year, raw.month, raw.day, tzinfo=timezone.utc)
    if not isinstance(raw, str):
        raise ValueError("config.yaml paper.date must be an ISO-8601 date string")
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"config.yaml paper.date is not an ISO-8601 date: {raw!r}") from exc
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=timezone.utc)


def generate_variables(
    config: dict[str, Any] | None = None,
    project_root: str | Path | None = None,
) -> dict[str, str]:
    """Compute the full ``{{TOKEN}} -> value`` map for the manuscript.

    Every value is a pure function of the config and the library registries.
    There is no clock override parameter because no token reads a clock: the
    dated token, ``CONFIG_MANUSCRIPT_DATE``, comes from
    :func:`manuscript_instant`.

    Args:
        config: Pre-loaded config mapping (avoids re-reading the file in
            tests); defaults to :func:`load_mission_config`.
        project_root: Root used to locate ``manuscript/config.yaml``.

    Returns:
        Mapping of token name to rendered string value.

    Raises:
        ValueError: If the config is missing the mission/paper sections or
            the schedule is invalid.
    """
    loaded = config if config is not None else load_mission_config(project_root)
    mission = loaded.get("mission")
    paper = loaded.get("paper")
    if not isinstance(mission, dict):
        raise ValueError("config.yaml mission section must be a mapping")
    if not isinstance(paper, dict):
        raise ValueError("config.yaml paper section must be a mapping")

    mission_schedule = mission.get("schedule")
    overlap_cfg = mission.get("overlap_window", mission_schedule)
    if not isinstance(mission_schedule, dict) or not isinstance(overlap_cfg, dict):
        raise ValueError("mission schedule and overlap_window must be mappings")
    start, end = parse_schedule(mission_schedule)
    seed = mission.get("default_seed", 0)
    num_codenames = mission.get("num_codenames", 3)
    sample = generate_codenames(num_codenames, seed=seed)
    # Overlap window defaults to the main schedule (full overlap) when absent.
    overlap_start, overlap_end = parse_schedule(overlap_cfg)
    overlap_hours = windows_overlap(start, end, overlap_start, overlap_end).total_seconds() / 3600
    scheme_sample = codenames_by_scheme(num_codenames, seed=seed, scheme="alliterative")
    # Alliterative capacity, computed from the bundled word lists rather than
    # quoted: the scheme can only emit pairs whose adjective and noun share an
    # initial, and it seeds each index independently, so samples may repeat.
    shared_initials = {adj[0] for adj in ADJECTIVES} & {noun[0] for noun in NOUNS}
    alliterative_pairs = {(adj, noun) for adj in ADJECTIVES for noun in NOUNS if adj[0] == noun[0]}
    manuscript_date = manuscript_instant(loaded).date().isoformat()

    testing = loaded.get("testing")
    if not isinstance(testing, dict):
        testing = {}
    coverage_gate = testing.get("coverage_gate_percent", DEFAULT_COVERAGE_GATE_PERCENT)
    max_failures = testing.get("max_test_failures", DEFAULT_MAX_TEST_FAILURES)

    return {
        "MISSION_CODENAME": str(mission.get("codename", "Q-BRANCH")),
        "PACKAGE_VERSION": str(paper.get("version", "0.1.0")),
        "CONFIG_DEFAULT_SEED": str(seed),
        "CONFIG_NUM_CODENAMES": str(num_codenames),
        "CONFIG_SCHEDULE_START": start.isoformat(timespec="seconds"),
        "CONFIG_SCHEDULE_END": end.isoformat(timespec="seconds"),
        "RESULT_WINDOW_HOURS": f"{(end - start).total_seconds() / 3600:.1f}",
        "RESULT_OVERLAP_HOURS": f"{overlap_hours:.1f}",
        "RESULT_CODENAME_SAMPLE": ", ".join(sample),
        "RESULT_SCHEME_SAMPLE": ", ".join(scheme_sample),
        "RESULT_SCHEME_DISTINCT": str(len(set(scheme_sample))),
        "ALLITERATIVE_INITIALS": str(len(shared_initials)),
        "ALLITERATIVE_CAPACITY": str(len(alliterative_pairs)),
        "CIPHER_COUNT": str(len(CIPHER_NAMES)),
        "CIPHER_NAMES_CSV": ", ".join(CIPHER_NAMES),
        "CIPHER_DESCRIPTION_TABLE": "\n".join(f"| {name} | {CIPHER_DESCRIPTIONS[name]} |" for name in CIPHER_NAMES),
        "CODENAME_SCHEMES": ", ".join(CODENAME_SCHEMES),
        "CODENAME_SCHEME_COUNT": str(len(CODENAME_SCHEMES)),
        "CRYPTANALYSIS_HELPERS": str(len(CRYPTANALYSIS_HELPERS)),
        "SEEDED_HELPER_COUNT": str(len(SEEDED_HELPERS)),
        "SEEDED_HELPERS_CSV": ", ".join(SEEDED_HELPERS),
        "NATO_EXAMPLE": nato_codename("QB7"),
        "WORDLIST_SIZE": f"{len(ADJECTIVES)} x {len(NOUNS)}",
        "WORDLIST_CAPACITY": str(len(ADJECTIVES) * len(NOUNS)),
        "COVERAGE_GATE_PERCENT": str(coverage_gate),
        "MAX_TEST_FAILURES": str(max_failures),
        "CONFIG_MANUSCRIPT_DATE": manuscript_date,
    }


__all__ = [
    "CONFIG_RELATIVE",
    "DEFAULT_COVERAGE_GATE_PERCENT",
    "DEFAULT_MAX_TEST_FAILURES",
    "load_mission_config",
    "manuscript_instant",
    "generate_variables",
]

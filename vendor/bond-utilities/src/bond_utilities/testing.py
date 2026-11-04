"""Shared test fixtures and helpers for every bond package.

Import-light by design: this module depends only on ``pytest`` plus the
standard library (and the pure ``codenames``/``randomness`` primitives), so
importing it never pulls numpy, matplotlib, or — critically — any mock
framework. Other bond packages can reuse these fixtures by importing this
module in their ``conftest.py``.
"""

from __future__ import annotations

import random
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from .codenames import generate_codenames
from .randomness import make_rng

#: Default seed used by the suite's shared fixtures.
DEFAULT_TEST_SEED = 20260804


@contextmanager
def temp_dir() -> Iterator[Path]:
    """Context manager yielding a fresh temporary directory (auto-cleaned).

    Example:
        >>> with temp_dir() as directory:
        ...     path = directory / "mission.json"
    """
    with tempfile.TemporaryDirectory() as raw:
        yield Path(raw)


def seeded_codenames(count: int = 5, seed: int | str = DEFAULT_TEST_SEED) -> list[str]:
    """Return deterministic codenames for a test run.

    Args:
        count: Number of codenames to generate.
        seed: Seed; defaults to :data:`DEFAULT_TEST_SEED`.

    Returns:
        A reproducible codename list.
    """
    return generate_codenames(count, seed=seed)


@pytest.fixture
def seeded_rng() -> random.Random:
    """A reproducible ``random.Random`` generator (seed = DEFAULT_TEST_SEED).

    Two tests (or two fixture usages) see identical draw sequences.
    """
    return make_rng(DEFAULT_TEST_SEED)


@pytest.fixture
def mission_record() -> dict[str, Any]:
    """A valid mission-record dict for persistence and reporting tests."""
    return {
        "mission_id": "M-001",
        "codename": "SILENT-JAGUAR",
        "seed": DEFAULT_TEST_SEED,
        "version": "0.1.0",
        "started_at": "2026-08-04T00:00:00+00:00",
        "parameters": {"target": "grid", "count": 3},
        "outcomes": {},
        "provenance": {},
    }


__all__ = [
    "DEFAULT_TEST_SEED",
    "temp_dir",
    "seeded_codenames",
    "seeded_rng",
    "mission_record",
]

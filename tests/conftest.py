"""Pytest configuration for the_world_is_not_enough (ELEKTRA) tests."""

import os
import sys

# Force headless backend for matplotlib in figure tests
os.environ.setdefault("MPLBACKEND", "Agg")

# Add src/ to the path so the documented per-project pytest command works from
# a clean environment. bond-api/bond-utilities are proper installed deps.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
for _path in (SRC,):
    if _path not in sys.path:
        sys.path.insert(0, _path)

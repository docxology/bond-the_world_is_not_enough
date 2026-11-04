"""Minimal deterministic matplotlib figure generators.

The BOND suite keeps figures deliberately small: one schedule-window chart
that any package can render from ``bond_utilities`` mission config values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt

from ..ciphers import letter_frequency
from ..clock import to_utc

#: Default figure output paths, relative to the current working directory.
DEFAULT_FIGURE_PATH = Path("output") / "figures" / "mission_schedule.png"
DEFAULT_FREQUENCY_PATH = Path("output") / "figures" / "letter_frequency.png"


def plot_mission_schedule(
    start: datetime,
    end: datetime,
    now: datetime | None = None,
    path: str | Path | None = None,
) -> Path:
    """Render a mission schedule window as a PNG and return its path.

    The chart draws one horizontal bar from ``start`` to ``end`` and a
    vertical "now" marker at ``now`` (default: current UTC time), plus
    window start/end labels.

    Args:
        start: Window start (naive treated as UTC).
        end: Window end (must not precede ``start``).
        now: Reference instant for the marker; defaults to current UTC.
        path: Output path; defaults to ``output/figures/mission_schedule.png``
            relative to the working directory.

    Returns:
        The absolute path of the written PNG.

    Raises:
        ValueError: If ``end`` precedes ``start``.
    """
    start_utc = to_utc(start)
    end_utc = to_utc(end)
    if end_utc < start_utc:
        raise ValueError("schedule end must not precede start")
    now_utc = to_utc(now) if now is not None else datetime.now(timezone.utc)

    target = Path(path) if path is not None else DEFAULT_FIGURE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    figure, axis = plt.subplots(figsize=(7.0, 1.8))
    duration = (end_utc - start_utc).total_seconds()
    axis.barh(
        [0],
        [duration],
        left=[start_utc.timestamp()],
        height=0.45,
        color="#1e3a8a",
        label="mission window",
    )
    axis.axvline(now_utc.timestamp(), color="#b91c1c", linestyle="--", linewidth=1.2)
    axis.set_xlim(start_utc.timestamp(), end_utc.timestamp())
    axis.set_yticks([])
    axis.set_xlabel("unix time (s)")
    axis.set_title("Mission schedule window")
    axis.text(
        start_utc.timestamp(),
        0.62,
        "start",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    axis.text(
        end_utc.timestamp(),
        0.62,
        "end",
        ha="right",
        va="bottom",
        fontsize=8,
    )
    figure.savefig(target, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return target.resolve()


def plot_frequency_analysis(text: str, path: str | Path | None = None) -> Path:
    """Render a letter-frequency bar chart for ``text`` and return the PNG path.

    The chart is fully deterministic — the same ``text`` always produces the
    same bytes (with the Agg backend).

    Args:
        text: Text whose A-Z letter counts are plotted.
        path: Output path; defaults to ``output/figures/letter_frequency.png``
            relative to the working directory.

    Returns:
        The absolute path of the written PNG.
    """
    counts = letter_frequency(text)
    target = Path(path) if path is not None else DEFAULT_FREQUENCY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    figure, axis = plt.subplots(figsize=(8.0, 3.0))
    letters = list(counts.keys())
    values = [counts[letter] for letter in letters]
    axis.bar(letters, values, color="#1e3a8a")
    axis.set_title("Letter frequency")
    axis.set_xlabel("letter")
    axis.set_ylabel("count")
    figure.savefig(target, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return target.resolve()


__all__ = ["DEFAULT_FIGURE_PATH", "DEFAULT_FREQUENCY_PATH", "plot_mission_schedule", "plot_frequency_analysis"]

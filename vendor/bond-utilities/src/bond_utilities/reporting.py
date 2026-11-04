"""Plain-text table and key/value reporting for thin CLIs.

Everything here writes to an explicit ``stream`` so callers and tests can
capture output without mocks — pass an ``io.StringIO`` in tests and assert on
real rendered text. ``stream=None`` (the default) resolves ``sys.stdout`` **at
call time**, so a caller that redirects stdout (``contextlib.redirect_stdout``,
pytest's ``capsys``) is honoured; binding the default at import time would
capture the original stdout object forever.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from datetime import datetime
from typing import TextIO

from .clock import MissionSchedule

Cell = object


def _resolve_stream(stream: TextIO | None) -> TextIO:
    """Return ``stream``, or the *current* ``sys.stdout`` when it is ``None``."""
    return sys.stdout if stream is None else stream


def banner(title: str, width: int = 60, fill: str = "=") -> str:
    """Return a centered ``title`` wrapped between two ``fill`` lines.

    Args:
        title: Text to center.
        width: Total line width (>= 4).
        fill: Single-character (or repeated) filler.

    Returns:
        A three-line banner string without a trailing newline.

    Raises:
        ValueError: If ``width`` is too small or ``fill`` is empty.
    """
    if width < 4:
        raise ValueError("width must be >= 4")
    if not fill:
        raise ValueError("fill must not be empty")
    line = fill * width
    return f"{line}\n{title.center(width)}\n{line}"


def format_table(
    rows: Sequence[Sequence[Cell]],
    headers: Sequence[str] | None = None,
) -> str:
    """Render ``rows`` as a left-aligned, fixed-width text table.

    Args:
        rows: Row cells; each cell is converted with ``str()``.
        headers: Optional header row, separated from data by dashes.

    Returns:
        The formatted table as a single string (no trailing newline),
        or an empty string when there are no rows and no headers.

    Raises:
        ValueError: If rows have inconsistent cell counts.
    """
    table: list[list[str]] = [[str(cell) for cell in row] for row in rows]
    # An empty header list is equivalent to no header: inserting an empty
    # row first would make the guard below reject every non-empty table as
    # ragged, which is not what the caller asked for.
    if headers is not None and not headers:
        headers = None
    if headers is not None:
        table.insert(0, [str(header) for header in headers])
    if table and any(len(row) != len(table[0]) for row in table):
        raise ValueError("all table rows must have the same number of cells")
    if not table:
        return ""
    widths = [max(len(row[index]) for row in table) for index in range(len(table[0]))]
    lines: list[str] = []
    for row_index, row in enumerate(table):
        cells = [cell.ljust(widths[index]) if index < len(widths) - 1 else cell for index, cell in enumerate(row)]
        lines.append("  ".join(cells))
        if headers is not None and row_index == 0:
            lines.append("  ".join("-" * len(cell) for cell in cells))
    return "\n".join(lines)


def format_kv(pairs: Sequence[tuple[str, Cell]]) -> str:
    """Render ``key: value`` pairs with right-aligned keys.

    Args:
        pairs: Sequence of ``(key, value)`` pairs; both are stringified.

    Returns:
        One ``key : value`` line per pair (keys aligned), no trailing newline.
    """
    items = [(str(key), str(value)) for key, value in pairs]
    if not items:
        return ""
    width = max(len(key) for key, _ in items)
    return "\n".join(f"{key.ljust(width)} : {value}" for key, value in items)


def print_table(
    rows: Sequence[Sequence[Cell]],
    headers: Sequence[str] | None = None,
    stream: TextIO | None = None,
) -> None:
    """Print :func:`format_table` output to ``stream`` (default: live stdout)."""
    print(format_table(rows, headers), file=_resolve_stream(stream))


def print_kv(
    pairs: Sequence[tuple[str, Cell]],
    stream: TextIO | None = None,
) -> None:
    """Print :func:`format_kv` output to ``stream`` (default: live stdout)."""
    print(format_kv(pairs), file=_resolve_stream(stream))


def schedule_table(
    schedules: Sequence[MissionSchedule],
    now: datetime | None = None,
    headers: Sequence[str] | None = None,
) -> str:
    """Render :class:`MissionSchedule` rows as a text table.

    Each row shows the schedule name, start, end, and status at ``now``.

    Args:
        schedules: Mission schedules to render.
        now: Reference instant for the status column; defaults to current UTC.
        headers: Optional column headers; default ``name/start/end/status``.

    Returns:
        A formatted table string.

    Raises:
        ValueError: If a row is not a :class:`MissionSchedule`.
    """
    default_headers = ["name", "start", "end", "status"]
    rows: list[list[str]] = []
    for schedule in schedules:
        if not isinstance(schedule, MissionSchedule):
            raise ValueError("schedule_table requires MissionSchedule rows")
        rows.append(
            [
                schedule.name,
                schedule.start.isoformat(timespec="seconds"),
                schedule.end.isoformat(timespec="seconds"),
                schedule.status(now=now),
            ]
        )
    return format_table(rows, headers=headers if headers is not None else default_headers)


def print_schedule_table(
    schedules: Sequence[MissionSchedule],
    now: datetime | None = None,
    stream: TextIO | None = None,
) -> None:
    """Print :func:`schedule_table` output to ``stream`` (default: live stdout)."""
    print(schedule_table(schedules, now=now), file=_resolve_stream(stream))


__all__ = [
    "banner",
    "format_table",
    "format_kv",
    "print_table",
    "print_kv",
    "schedule_table",
    "print_schedule_table",
]

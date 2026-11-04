"""Mission elapsed-time and schedule-window utilities.

All functions accept timezone-aware datetimes; naive datetimes are treated
as UTC (documented, deterministic). Wall-clock defaults (``now=None``) are
provided only where the semantics are inherently about "right now" — tests
always pass explicit ``now`` values so behavior is fully deterministic.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

_DAY_SECONDS = 86400
_DURATION_UNITS: tuple[tuple[str, int], ...] = (("d", 86400), ("h", 3600), ("m", 60), ("s", 1))


def to_utc(value: datetime) -> datetime:
    """Return ``value`` as a timezone-aware UTC datetime.

    Naive datetimes are assumed to already be UTC (documented convention);
    aware datetimes are converted to UTC.

    Args:
        value: Any datetime.

    Returns:
        An equivalent, timezone-aware datetime in UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_timestamp(text: str) -> datetime:
    """Parse an ISO-8601 timestamp, accepting a trailing ``Z``.

    Args:
        text: ISO-8601 string such as ``"2026-08-04T00:00:00Z"``.

    Returns:
        A timezone-aware UTC datetime.

    Raises:
        ValueError: If ``text`` is not a parseable timestamp.
    """
    if not isinstance(text, str):
        raise ValueError(f"timestamp must be a string, got {type(text).__name__}")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    return to_utc(datetime.fromisoformat(normalized))


def elapsed_time(start: datetime, end: datetime) -> timedelta:
    """Return ``end - start`` as a non-negative duration.

    Args:
        start: Mission start (naive treated as UTC).
        end: Mission end (naive treated as UTC).

    Returns:
        ``end - start``.

    Raises:
        ValueError: If ``end`` precedes ``start``.
    """
    delta = to_utc(end) - to_utc(start)
    if delta < timedelta(0):
        raise ValueError("elapsed end must not precede start")
    return delta


def format_elapsed(delta: timedelta) -> str:
    """Format a duration as ``[Nd ]HH:MM:SS`` (the day part is omitted when zero).

    Args:
        delta: A non-negative duration.

    Returns:
        The formatted duration string.

    Raises:
        ValueError: If ``delta`` is negative.
    """
    if delta < timedelta(0):
        raise ValueError("cannot format a negative duration")
    total = int(delta.total_seconds())
    days, remainder = divmod(total, _DAY_SECONDS)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days:
        return f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def window_open(
    start: datetime,
    end: datetime,
    now: datetime | None = None,
) -> bool:
    """Return True when ``now`` falls inside the half-open window ``[start, end)``.

    Args:
        start: Window start.
        end: Window end (must not precede ``start``).
        now: Reference instant; defaults to the current UTC time.

    Returns:
        True if ``start <= now < end``.

    Raises:
        ValueError: If ``end`` precedes ``start``.
    """
    start_utc, end_utc = to_utc(start), to_utc(end)
    if end_utc < start_utc:
        raise ValueError("window end must not precede start")
    current = to_utc(now) if now is not None else datetime.now(timezone.utc)
    return start_utc <= current < end_utc


def window_elapsed(start: datetime, now: datetime | None = None) -> timedelta:
    """Return the time elapsed since window ``start``, clamped at zero.

    Args:
        start: Window start.
        now: Reference instant; defaults to the current UTC time.

    Returns:
        ``now - start`` when positive, otherwise zero.
    """
    delta = (to_utc(now) if now is not None else datetime.now(timezone.utc)) - to_utc(start)
    return delta if delta > timedelta(0) else timedelta(0)


def window_remaining(end: datetime, now: datetime | None = None) -> timedelta:
    """Return the time remaining until window ``end``, clamped at zero.

    Args:
        end: Window end.
        now: Reference instant; defaults to the current UTC time.

    Returns:
        ``end - now`` when positive, otherwise zero.
    """
    delta = to_utc(end) - (to_utc(now) if now is not None else datetime.now(timezone.utc))
    return delta if delta > timedelta(0) else timedelta(0)


def t_minus(target: datetime, now: datetime | None = None) -> str:
    """Render a ``T-`` countdown (or ``T+`` count-up) relative to ``target``.

    Args:
        target: The target instant.
        now: Reference instant; defaults to the current UTC time.

    Returns:
        ``"T-{elapsed}"`` while ``now`` precedes the target, otherwise
        ``"T+{elapsed}"`` (including at the exact target instant).
    """
    target_utc = to_utc(target)
    current = to_utc(now) if now is not None else datetime.now(timezone.utc)
    if target_utc >= current:
        return f"T-{format_elapsed(target_utc - current)}"
    return f"T+{format_elapsed(current - target_utc)}"


def parse_schedule(schedule: dict) -> tuple[datetime, datetime]:
    """Extract ``(start, end)`` aware UTC datetimes from a mission schedule.

    Args:
        schedule: Mapping with ISO-8601 ``start`` and ``end`` keys.

    Returns:
        The ``(start, end)`` pair, both normalized to UTC.

    Raises:
        ValueError: If the mapping is invalid, a key is missing, a value is
            not a parseable timestamp, or ``end`` precedes ``start``.
    """
    if not isinstance(schedule, dict):
        raise ValueError("schedule must be a mapping")
    try:
        start_text = schedule["start"]
        end_text = schedule["end"]
    except KeyError as exc:
        raise ValueError(f"schedule missing required key {exc.args[0]!r}") from exc
    start = parse_timestamp(start_text)
    end = parse_timestamp(end_text)
    if end < start:
        raise ValueError("schedule end must not precede start")
    return start, end


def windows_overlap(
    a_start: datetime,
    a_end: datetime,
    b_start: datetime,
    b_end: datetime,
) -> timedelta:
    """Return the duration common to two half-open windows (clamped at zero).

    Args:
        a_start: Start of the first window.
        a_end: End of the first window.
        b_start: Start of the second window.
        b_end: End of the second window.

    Returns:
        The overlap ``timedelta``; ``timedelta(0)`` when the windows are
        disjoint or only touch at an endpoint.

    Raises:
        ValueError: If either window's end precedes its start.
    """
    a_start_utc, a_end_utc = to_utc(a_start), to_utc(a_end)
    b_start_utc, b_end_utc = to_utc(b_start), to_utc(b_end)
    if a_end_utc < a_start_utc:
        raise ValueError("window A end must not precede start")
    if b_end_utc < b_start_utc:
        raise ValueError("window B end must not precede start")
    overlap = min(a_end_utc, b_end_utc) - max(a_start_utc, b_start_utc)
    return overlap if overlap > timedelta(0) else timedelta(0)


def merge_windows(windows: Sequence[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Merge overlapping windows into a minimal, sorted cover.

    The input is a sequence of ``(start, end)`` pairs. Windows that overlap
    or touch are merged; the result is sorted by start.

    Args:
        windows: Sequence of ``(start, end)`` pairs (each end >= start).

    Returns:
        A minimal sorted list of merged ``(start, end)`` UTC pairs.

    Raises:
        ValueError: If any window's end precedes its start.
    """
    normalized: list[tuple[datetime, datetime]] = []
    for start, end in windows:
        start_utc, end_utc = to_utc(start), to_utc(end)
        if end_utc < start_utc:
            raise ValueError("window end must not precede start")
        normalized.append((start_utc, end_utc))
    normalized.sort(key=lambda pair: pair[0])
    merged: list[tuple[datetime, datetime]] = []
    for start, end in normalized:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def parse_duration(text: str) -> timedelta:
    """Parse a compact duration like ``"1d 2h30m"`` / ``"90m"`` / ``"45s"``.

    Supports the units ``d``/``h``/``m``/``s`` in any order, with optional
    whitespace between components; bare integers are invalid.

    Args:
        text: The duration string (case-insensitive).

    Returns:
        The parsed ``timedelta`` (non-negative).

    Raises:
        ValueError: If ``text`` is empty or contains an invalid segment.
    """
    if not text or not text.strip():
        raise ValueError("duration text must not be empty")
    remaining = text.strip().lower()
    total = 0
    units = dict(_DURATION_UNITS)
    while remaining:
        match = re.match(r"(\d+)([dhms])", remaining)
        if match is None:
            raise ValueError(f"invalid duration segment in {text!r}")
        total += int(match.group(1)) * units[match.group(2)]
        remaining = remaining[match.end() :].lstrip()
    return timedelta(seconds=total)


def schedule_status(start: datetime, end: datetime, now: datetime | None = None) -> str:
    """Classify a window at ``now`` as ``PENDING``, ``ACTIVE``, or ``COMPLETE``.

    Args:
        start: Window start.
        end: Window end (must not precede ``start``).
        now: Reference instant; defaults to the current UTC time.

    Returns:
        ``"PENDING"`` before the start, ``"ACTIVE"`` inside ``[start, end)``,
        and ``"COMPLETE"`` from ``end`` onward.

    Raises:
        ValueError: If ``end`` precedes ``start``.
    """
    start_utc, end_utc = to_utc(start), to_utc(end)
    if end_utc < start_utc:
        raise ValueError("window end must not precede start")
    current = to_utc(now) if now is not None else datetime.now(timezone.utc)
    if current < start_utc:
        return "PENDING"
    if current < end_utc:
        return "ACTIVE"
    return "COMPLETE"


@dataclass(frozen=True)
class MissionSchedule:
    """A named mission window with status helpers.

    Example:
        >>> window = MissionSchedule("grid", parse_timestamp("2026-08-04T00:00:00Z"),
        ...                          parse_timestamp("2026-08-06T00:00:00Z"))
        >>> window.status(now=parse_timestamp("2026-08-05T00:00:00Z"))
        'ACTIVE'
    """

    name: str
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if to_utc(self.end) < to_utc(self.start):
            raise ValueError("schedule end must not precede start")

    @classmethod
    def from_config(cls, name: str, schedule: dict) -> "MissionSchedule":
        """Build a schedule from a ``{start, end}`` config mapping."""
        start, end = parse_schedule(schedule)
        return cls(name=name, start=start, end=end)

    @property
    def duration(self) -> timedelta:
        """The window duration (end - start)."""
        return to_utc(self.end) - to_utc(self.start)

    def open(self, now: datetime | None = None) -> bool:
        """True when ``now`` falls in the half-open window."""
        return window_open(self.start, self.end, now=now)

    def elapsed(self, now: datetime | None = None) -> timedelta:
        """Time since the window start, clamped at zero."""
        return window_elapsed(self.start, now=now)

    def remaining(self, now: datetime | None = None) -> timedelta:
        """Time until the window end, clamped at zero."""
        return window_remaining(self.end, now=now)

    def countdown(self, now: datetime | None = None) -> str:
        """A ``T-`` countdown to the window start (or ``T+`` after it)."""
        return t_minus(self.start, now=now)

    def status(self, now: datetime | None = None) -> str:
        """One of ``PENDING`` / ``ACTIVE`` / ``COMPLETE`` at ``now``."""
        return schedule_status(self.start, self.end, now=now)


__all__ = [
    "to_utc",
    "parse_timestamp",
    "elapsed_time",
    "format_elapsed",
    "window_open",
    "window_elapsed",
    "window_remaining",
    "t_minus",
    "parse_schedule",
    "windows_overlap",
    "merge_windows",
    "parse_duration",
    "schedule_status",
    "MissionSchedule",
]

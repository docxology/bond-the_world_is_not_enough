"""Energy-infrastructure model: DC power flow and cascading blackout.

ELEKTRA's fourth pillar models the power system that the film's plot depends
on — the pumped crude corridor, the hijacked submarine's support base, and the
city all draw from the same grid, so a coordinated blackout is the saboteur's
force multiplier. Two layers of real, deterministic mathematics:

* **DC power flow** — a linearized load-flow solution. With bus susceptance
  matrix :math:`B`, the nodal angle vector solves
  :math:`B'\\theta' = P'` (slack bus removed), and the active-power flow on
  each line ``(i, j)`` is :math:`F_{ij} = b_{ij}(\\theta_i - \\theta_j)`.

* **Cascading failure** — a deterministic outage cascade in the spirit of the
  OPA blackout model [@dobson_op]: an initial line outage reroutes power; the
  most-overloaded surviving line trips; the system re-solves until no line
  exceeds its thermal limit. The blackout is measured as the load islanded
  from the slack bus (lost load, MW, and its fraction of total load).

The canonical dataset is a two-area corridor whose strong interconnector is
the target: taking it out forces all transfer onto a weak tie that overloads
and trips, islanding the whole load area. Everything is deterministic — no
random draws, no external calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np

__all__ = [
    "GridLine",
    "PowerGrid",
    "cascade_failure",
    "dc_power_flow",
    "default_power_grid",
    "grid_connectivity",
    "grid_fingerprint",
    "total_load",
]


@dataclass(frozen=True)
class GridLine:
    """A transmission line ``source -> target`` with susceptance and thermal limit.

    ``susceptance`` is the line reactance inverse (p.u.), ``capacity_mw`` the
    thermal rating that triggers tripping when exceeded (times an overload
    factor). Bus indices reference :class:`PowerGrid` buses.
    """

    source: int
    target: int
    susceptance: float
    capacity_mw: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.source, bool)
            or not isinstance(self.source, int)
            or self.source < 0
        ):
            raise ValueError("GridLine.source must be a non-negative int")
        if (
            isinstance(self.target, bool)
            or not isinstance(self.target, int)
            or self.target < 0
        ):
            raise ValueError("GridLine.target must be a non-negative int")
        if self.source == self.target:
            raise ValueError("GridLine cannot be a self-loop")
        if self.susceptance <= 0:
            raise ValueError(
                f"GridLine.susceptance must be positive, got {self.susceptance}"
            )
        if self.capacity_mw <= 0:
            raise ValueError(
                f"GridLine.capacity_mw must be positive, got {self.capacity_mw}"
            )

    @property
    def id(self) -> str:
        """Deterministic line identifier ``source->target``."""
        return f"{self.source}->{self.target}"


@dataclass
class PowerGrid:
    """A DC power-flow network: buses, lines, and net nodal injections (MW).

    ``injections[i]`` is generation minus load at bus ``i`` (positive =
    generation); the entries must sum to zero. ``slack_bus`` provides the angle
    reference and absorbs the residual imbalance.
    """

    n_buses: int
    lines: list[GridLine] = field(default_factory=list)
    injections: list[float] = field(default_factory=list)
    slack_bus: int = 0

    def __post_init__(self) -> None:
        if (
            isinstance(self.n_buses, bool)
            or not isinstance(self.n_buses, int)
            or self.n_buses < 2
        ):
            raise ValueError("PowerGrid.n_buses must be an int >= 2")
        if isinstance(self.slack_bus, bool) or not isinstance(self.slack_bus, int):
            raise TypeError("PowerGrid.slack_bus must be an int")
        if not 0 <= self.slack_bus < self.n_buses:
            raise ValueError("PowerGrid.slack_bus out of range")
        if len(self.injections) != self.n_buses:
            raise ValueError(
                f"PowerGrid.injections must have one entry per bus ({self.n_buses}), "
                f"got {len(self.injections)}"
            )
        for injection in self.injections:
            if isinstance(injection, bool) or not isinstance(injection, (int, float)):
                raise TypeError("PowerGrid.injections must be numeric")
        if abs(sum(self.injections)) > 1e-6:
            raise ValueError(
                f"PowerGrid.injections must balance (sum 0), got sum {sum(self.injections):g}"
            )
        self._line_by_id: dict[str, GridLine] = {}
        for line in self.lines:
            if not isinstance(line, GridLine):
                raise TypeError("PowerGrid.lines must contain GridLine instances")
            if line.source >= self.n_buses or line.target >= self.n_buses:
                raise ValueError(
                    f"GridLine {line.id!r} references a bus outside 0..{self.n_buses - 1}"
                )
            if line.id in self._line_by_id:
                raise ValueError(f"duplicate line {line.id!r} in power grid")
            self._line_by_id[line.id] = line

    def line_id(self, line_id: str) -> GridLine:
        """Look up a line by its ``source->target`` id."""
        try:
            return self._line_by_id[line_id]
        except KeyError:
            raise KeyError(f"no grid line {line_id!r} in power grid") from None

    def with_lines(self, lines: list[GridLine]) -> PowerGrid:
        """A copy of this grid restricted to ``lines`` (used by the cascade)."""
        return PowerGrid(
            n_buses=self.n_buses,
            lines=list(lines),
            injections=list(self.injections),
            slack_bus=self.slack_bus,
        )


def default_power_grid() -> PowerGrid:
    """The canonical ELEKTRA power dataset: an 8-bus, two-area corridor.

    Area A (buses 0-4) hosts both generators; Area B (buses 5-7) is pure load
    (220 MW). Two interconnectors tie the areas: the strong ``3->5`` line
    (400 MW rating) and the weak ``4->5`` line (150 MW). Under intact
    operation both share the transfer and stay within limits; knocking out the
    strong tie forces the whole Area-B load onto the weak tie, which
    overloads, trips, and islands Area B — the coordinated-blackout scenario.
    """
    return PowerGrid(
        n_buses=8,
        lines=[
            GridLine(0, 2, 5.0, 300.0),
            GridLine(0, 3, 5.0, 300.0),
            GridLine(1, 3, 5.0, 300.0),
            GridLine(1, 4, 5.0, 300.0),
            GridLine(2, 4, 5.0, 200.0),
            GridLine(3, 5, 10.0, 400.0),  # strong interconnector (target)
            GridLine(4, 5, 10.0, 150.0),  # weak interconnector
            GridLine(5, 6, 5.0, 200.0),
            GridLine(5, 7, 5.0, 200.0),
            GridLine(6, 7, 5.0, 150.0),
        ],
        injections=[250.0, 250.0, -120.0, -100.0, -60.0, -90.0, -70.0, -60.0],
        slack_bus=0,
    )


def _susceptance_matrix(grid: PowerGrid) -> np.ndarray:
    """Build the full DC susceptance matrix ``B`` (n x n)."""
    b = np.zeros((grid.n_buses, grid.n_buses), dtype=np.float64)
    for line in grid.lines:
        b[line.source, line.source] += line.susceptance
        b[line.target, line.target] += line.susceptance
        b[line.source, line.target] -= line.susceptance
        b[line.target, line.source] -= line.susceptance
    return b


def dc_power_flow(grid: PowerGrid) -> dict[str, Any]:
    """Solve the linearized DC power flow and return angles and line flows.

    The slack bus sets ``theta_slack = 0``; the reduced system
    ``B' theta' = P'`` is solved with Gaussian elimination (``numpy.linalg.solve``),
    deterministic for a fixed dataset. Only the slack-connected live component
    is solved: islanded buses (separated by an outage cascade) are dead, carry
    no power, and their injections are unserved. Returns per-line directed
    flows ``F_ij = b_ij (theta_i - theta_j)`` in MW.
    """
    if not grid.lines:
        raise ValueError("dc_power_flow requires at least one line")
    # grid_connectivity() seeds its search at the slack bus, so the slack bus is
    # always a member of `connected` — no separate "slack islanded" branch is
    # possible (a guard for it would be dead code that silently returned an
    # empty flow map).
    connected = grid_connectivity(grid)
    theta: np.ndarray = np.zeros(grid.n_buses, dtype=np.float64)
    solve_buses = [bus for bus in sorted(connected) if bus != grid.slack_bus]
    flows: dict[str, float] = {}
    if not solve_buses:
        # only the slack bus remains live — total blackout, no line carries power
        return {
            "theta": [float(v) for v in theta],
            "flows": flows,
            "slack_bus": grid.slack_bus,
        }
    b = _susceptance_matrix(grid)
    b_reduced = b[np.ix_(solve_buses, solve_buses)]
    p_reduced = np.asarray([grid.injections[i] for i in solve_buses], dtype=np.float64)
    theta_reduced = np.linalg.solve(b_reduced, p_reduced)
    theta[solve_buses] = theta_reduced

    for line in grid.lines:
        if line.source in connected and line.target in connected:
            flows[line.id] = float(
                line.susceptance * (theta[line.source] - theta[line.target])
            )
    return {
        "theta": [float(value) for value in theta],
        "flows": flows,
        "slack_bus": grid.slack_bus,
    }


def grid_connectivity(grid: PowerGrid) -> set[int]:
    """Buses reachable from the slack bus over the grid's lines (undirected)."""
    adjacency: dict[int, list[int]] = {bus: [] for bus in range(grid.n_buses)}
    for line in grid.lines:
        adjacency[line.source].append(line.target)
        adjacency[line.target].append(line.source)
    seen: set[int] = set()
    stack = [grid.slack_bus]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adjacency[node])
    return seen


def total_load(grid: PowerGrid) -> float:
    """Total connected load: the sum of magnitudes of negative injections (MW)."""
    return float(sum(-injection for injection in grid.injections if injection < 0))


def cascade_failure(
    grid: PowerGrid,
    initial_outage: str,
    *,
    overload_factor: float = 1.0,
    max_steps: int = 20,
) -> dict[str, Any]:
    """Deterministic outage cascade: ``initial_outage`` then sequential tripping.

    Each step re-solves the DC flow over the surviving lines; the most
    overloaded line (largest ``|flow| / capacity`` ratio, ties broken by line
    order) trips. The cascade stops when no line exceeds
    ``overload_factor * capacity`` or ``max_steps`` is reached. The blackout is
    the load islanded from the slack bus.

    Returns the tripped lines (including the initial outage), the cascade
    step count, the lost load (MW), and its fraction of total load.
    """
    if not 0 < overload_factor:
        raise ValueError("overload_factor must be positive")
    if max_steps < 1:
        raise ValueError("max_steps must be >= 1")
    grid.line_id(initial_outage)  # raises KeyError for an unknown line

    active = [line for line in grid.lines if line.id != initial_outage]
    tripped: list[str] = [initial_outage]
    steps = 0
    stable = False
    for _ in range(max_steps):
        if not active:
            break
        solution = dc_power_flow(grid.with_lines(active))
        flows = cast("dict[str, float]", solution["flows"])
        overloads = [
            line
            for line in active
            if abs(flows.get(line.id, 0.0)) > overload_factor * line.capacity_mw
        ]
        if not overloads:
            stable = True
            break
        worst = max(
            overloads,
            key=lambda line: (abs(flows.get(line.id, 0.0)) / line.capacity_mw, line.id),
        )
        active = [line for line in active if line.id != worst.id]
        tripped.append(worst.id)
        steps += 1

    surviving = grid.with_lines(active)
    connected = grid_connectivity(surviving)
    lost_load = sum(
        -injection
        for bus, injection in enumerate(grid.injections)
        if bus not in connected and injection < 0
    )
    total = total_load(grid)
    return {
        "tripped": tuple(tripped),
        "steps": steps,
        "stable": stable,
        "lost_load_mw": lost_load,
        "blackout_fraction": lost_load / total if total > 0 else 0.0,
        "surviving_lines": tuple(line.id for line in active),
    }


def grid_fingerprint(grid: PowerGrid) -> str:
    """Stable textual fingerprint of grid topology, ratings, and injections."""
    line_lines = sorted(
        f"{line.source}|{line.target}|{line.susceptance:g}|{line.capacity_mw:g}"
        for line in grid.lines
    )
    return "|".join(
        [
            str(grid.n_buses),
            str(grid.slack_bus),
            ",".join(f"{v:g}" for v in grid.injections),
            *line_lines,
        ]
    )

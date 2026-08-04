"""Nuclear-submarine defense: passive-sonar detection and evasion routing.

ELEKTRA's second pillar models a nuclear submarine under threat of detection
and attack (in the film, the submarine *King William* is hijacked and must be
recovered / denied). Two layers of real, deterministic mathematics:

* **Detection physics** — a simplified passive-sonar equation computes the
  received signal-to-noise ratio of the target's radiated noise as a function
  of range, and a normal-CDF link (implemented with :func:`math.erf`, no SciPy)
  turns SNR into a detection probability per listening sensor. This drives an
  exposure risk field over a 2-D patrol grid.

* **Evasion routing** — Dijkstra's shortest-path search over that risk field,
  where the edge cost is the cumulative detection probability of crossing each
  cell. The mission compares the exposure of the least-risk route against a
  naive straight-line (Bresenham) run to quantify how much hiding in the
  acoustic shadow buys.

* **Bearing-only triangulation** — a closed-form least-squares intersection of
  two bearing lines locates an emitter (e.g. the hijacked boat) from two
  passive observations.

Everything is deterministic: sensors, the grid, and the sonar parameters are
fixed inputs, and no random draws are made.
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

import numpy as np

__all__ = [
    "Sensor",
    "build_risk_map",
    "detection_probability",
    "dijkstra_evasion",
    "evasion_analysis",
    "normal_cdf",
    "passive_sonar_snr",
    "scenario_fingerprint",
    "straight_line_path",
    "triangulate_bearings",
]


def normal_cdf(x: float | np.ndarray) -> float | np.ndarray:
    """Standard-normal CDF via the exact error function, ``Phi(x)``.

    Accepts a scalar or a NumPy array (vectorised through ``math.erf``),
    returning a float for scalar input and an array for array input.
    """
    if np.ndim(x) == 0:
        return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))
    vectorized = np.vectorize(math.erf)
    out = 0.5 * (1.0 + vectorized(np.asarray(x) / math.sqrt(2.0)))
    return cast("float | np.ndarray", out)


@dataclass(frozen=True)
class Sensor:
    """A listening sensor (patrol, picket, towed array) at a grid position.

    ``source_level`` is the radiated noise it must detect (dB re 1 uPa @ 1 m),
    ``noise_level`` the ambient/self noise, ``directivity_index`` its array
    gain, and ``detection_threshold_db`` the DT of its operator. Bounds are
    validated on construction.
    """

    x: int
    y: int
    source_level: float = 150.0
    noise_level: float = 65.0
    directivity_index: float = 0.0
    detection_threshold_db: float = 10.0
    absorption_db_per_km: float = 0.05

    def __post_init__(self) -> None:
        if not isinstance(self.x, int) or isinstance(self.x, bool) or self.x < 0:
            raise ValueError("Sensor.x must be a non-negative int")
        if not isinstance(self.y, int) or isinstance(self.y, bool) or self.y < 0:
            raise ValueError("Sensor.y must be a non-negative int")
        if self.source_level < 0:
            raise ValueError("Sensor.source_level must be non-negative")
        if self.noise_level < 0:
            raise ValueError("Sensor.noise_level must be non-negative")


def passive_sonar_snr(
    source_level: float,
    range_m: float | np.ndarray,
    *,
    absorption_db_per_km: float = 0.05,
    noise_level: float = 65.0,
    directivity_index: float = 0.0,
) -> float | np.ndarray:
    """Received signal-to-noise ratio (dB) at ``range_m`` via a simplified passive equation.

    ``SNR = SL - TL - NL + DI`` with transmission loss
    ``TL = 20*log10(r_km) + alpha*r_km`` (spherical spreading plus absorption),
    where ``r_km = max(range, 1)/1000`` keeps the reference at 1 m. Monotone
    decreasing in range for physically sensible absorption. Accepts scalars or
    arrays (the risk-map grid is vectorised through this function).
    """
    if np.ndim(range_m) == 0 and range_m < 0:
        raise ValueError("range_m must be non-negative")
    r_km = np.maximum(np.asarray(range_m, dtype=np.float64), 1.0) / 1000.0
    spreading = 20.0 * np.log10(np.maximum(r_km, 1e-12))
    absorption = absorption_db_per_km * r_km
    tl = spreading + absorption
    return source_level - tl - noise_level + directivity_index


def detection_probability(
    snr: float | np.ndarray,
    detection_threshold_db: float = 10.0,
    sigma_db: float = 6.0,
) -> float | np.ndarray:
    """Probability that a contact with ``snr`` dB is detected and classified.

    ``P_d = Phi((SNR - DT)/sigma)`` using the normal CDF, a standard operator
    performance-curve approximation. Bounded to [0, 1] by construction;
    accepts scalars or arrays.
    """
    if detection_threshold_db < 0:
        raise ValueError("detection_threshold_db must be non-negative")
    if sigma_db <= 0:
        raise ValueError("sigma_db must be positive")
    return normal_cdf((snr - detection_threshold_db) / sigma_db)


def build_risk_map(
    grid_size: int, sensors: tuple[Sensor, ...], step_m: float = 1000.0
) -> np.ndarray:
    """Compute the per-cell detection-probability risk field over a ``grid_size`` square.

    Each cell's value is ``1 - prod(1 - P_i)`` over all sensors (independent
    detections), where each ``P_i`` uses that sensor's passive-sonar link at
    the cell-to-sensor range. Shape ``(grid_size, grid_size)``; row 0 = y = 0.
    """
    if grid_size < 2:
        raise ValueError("grid_size must be >= 2")
    risk = np.zeros((grid_size, grid_size), dtype=np.float64)
    ys, xs = np.mgrid[0:grid_size, 0:grid_size]
    for sensor in sensors:
        d = np.hypot(xs - sensor.x, ys - sensor.y) * step_m
        snr_grid = passive_sonar_snr(
            sensor.source_level,
            d,
            absorption_db_per_km=sensor.absorption_db_per_km,
            noise_level=sensor.noise_level,
            directivity_index=sensor.directivity_index,
        )
        p = detection_probability(snr_grid, sensor.detection_threshold_db)
        risk = 1.0 - (1.0 - risk) * (1.0 - p)
    return risk


@dataclass(frozen=True)
class EvasionResult:
    """Output of an evasion search: the route, its cumulative exposure, and path length."""

    path: tuple[tuple[int, int], ...]
    cumulative_exposure: float
    path_length: int

    def as_dict(self) -> dict[str, object]:
        return {
            "path": [list(point) for point in self.path],
            "cumulative_exposure": self.cumulative_exposure,
            "path_length": self.path_length,
        }


def _in_bounds(grid_size: int, point: tuple[int, int]) -> bool:
    x, y = point
    return 0 <= x < grid_size and 0 <= y < grid_size


def dijkstra_evasion(
    risk: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> EvasionResult:
    """Least-exposure path from ``start`` to ``goal`` via Dijkstra's algorithm.

    Edge cost for moving into a cell is its detection risk plus a tiny epsilon
    tie-breaker; movement is 4-connected. Total path cost excludes the start
    cell and includes the goal. Deterministic: ties resolve by lexicographic
    node order through a stable cost + insertion counter.
    """
    grid_size = risk.shape[0]
    if risk.shape[0] != risk.shape[1]:
        raise ValueError("risk map must be square")
    if not _in_bounds(grid_size, start):
        raise ValueError(
            f"start {start} out of bounds for {grid_size}x{grid_size} grid"
        )
    if not _in_bounds(grid_size, goal):
        raise ValueError(f"goal {goal} out of bounds for {grid_size}x{grid_size} grid")
    if start == goal:
        return EvasionResult(path=(start,), cumulative_exposure=0.0, path_length=1)

    infinity = float("inf")
    dist: dict[tuple[int, int], float] = {start: 0.0}
    prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    counter = 0
    # heap entries: (cost, counter, node) — counter breaks cost ties deterministically
    heap: list[tuple[float, int, tuple[int, int]]] = [(0.0, counter, start)]
    counter += 1
    visited: set[tuple[int, int]] = set()

    while heap:
        cost, _, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        if node == goal:
            break
        x, y = node
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y + dy)
            if not _in_bounds(grid_size, nxt):
                continue
            step_cost = float(risk[nxt[1], nxt[0]])
            new_cost = cost + step_cost
            if new_cost < dist.get(nxt, infinity):
                dist[nxt] = new_cost
                prev[nxt] = node
                heapq.heappush(heap, (new_cost, counter, nxt))
                counter += 1

    if goal not in dist:
        raise ValueError(
            "no path exists between start and goal (disconnected risk field)"
        )
    path: list[tuple[int, int]] = []
    cur: tuple[int, int] | None = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return EvasionResult(
        path=tuple(path),
        cumulative_exposure=float(dist[goal]),
        path_length=len(path),
    )


def straight_line_path(
    start: tuple[int, int],
    goal: tuple[int, int],
) -> tuple[tuple[int, int], ...]:
    """Deterministic 4-connected monotone baseline path (no diagonal hops).

    Moves greedily toward the goal, preferring the axis with the larger
    remaining distance. Because it stays on the same 4-connected grid Dijkstra
    searches, the least-risk route can always match or beat it — the
    self-gauging comparison is fair by construction.
    """
    if start == goal:
        return (start,)
    x, y = start
    path: list[tuple[int, int]] = [(x, y)]
    while (x, y) != goal:
        dx = goal[0] - x
        dy = goal[1] - y
        if abs(dx) >= abs(dy):
            x += 1 if dx > 0 else -1
        else:
            y += 1 if dy > 0 else -1
        path.append((x, y))
    return tuple(path)


def _path_exposure(
    risk: np.ndarray,
    path: tuple[tuple[int, int], ...],
) -> float:
    total = 0.0
    for x, y in path[1:]:
        total += float(risk[y, x])
    return total


def evasion_analysis(
    risk: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> dict[str, object]:
    """Compare naive straight-line vs. least-risk evasion routing.

    Returns both exposures, the relative reduction, and the optimized route.
    The straight-line baseline is included so the analysis is self-gauging.
    """
    direct = straight_line_path(start, goal)
    naive_exposure = _path_exposure(risk, direct)
    routed = dijkstra_evasion(risk, start, goal)
    optimal_exposure = routed.cumulative_exposure
    reduction = (
        (naive_exposure - optimal_exposure) / naive_exposure
        if naive_exposure > 0
        else 0.0
    )
    return {
        "naive_exposure": naive_exposure,
        "optimal_exposure": optimal_exposure,
        "exposure_reduction": reduction,
        "naive_path_length": len(direct),
        "optimal_path_length": routed.path_length,
        "routed_path": [list(p) for p in routed.path],
    }


def triangulate_bearings(
    pos1: tuple[float, float],
    bearing1_deg: float,
    pos2: tuple[float, float],
    bearing2_deg: float,
) -> tuple[float, float] | None:
    """Locate an emitter from two passive bearing observeds (least-squares line intersection).

    Each observation is a line through ``pos`` with direction
    ``(cos, sin)`` of ``bearing_deg`` (degrees, compass: 0 = +x, 90 = +y).
    Returns the point closest to both lines, or ``None`` if the bearings are
    parallel (no unique fix).
    """
    for pos in (pos1, pos2):
        if len(pos) != 2:
            raise ValueError("observation positions must be (x, y) pairs")
    r1 = math.radians(bearing1_deg)
    r2 = math.radians(bearing2_deg)
    d1 = (math.cos(r1), math.sin(r1))
    d2 = (math.cos(r2), math.sin(r2))
    # Plane-line intersection: solve for alpha,beta minimizing the gap.
    # Normal equations for the two closest-point parameters.
    denom = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(denom) < 1e-9:
        return None
    delta = (pos2[0] - pos1[0], pos2[1] - pos1[1])
    alpha = (delta[0] * d2[1] - delta[1] * d2[0]) / denom
    beta = (delta[0] * d1[1] - delta[1] * d1[0]) / denom
    p1 = (pos1[0] + alpha * d1[0], pos1[1] + alpha * d1[1])
    p2 = (pos2[0] + beta * d2[0], pos2[1] + beta * d2[1])
    return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)


def scenario_fingerprint(
    grid_size: int,
    sensors: tuple[Sensor, ...],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> str:
    """Stable fingerprint of a detection/evasion scenario (for provenance hashing)."""
    sensor_lines = sorted(
        f"{s.x},{s.y}|{s.source_level}|{s.noise_level}|{s.detection_threshold_db}"
        for s in sensors
    )
    return "|".join(
        [
            str(grid_size),
            f"{start[0]},{start[1]}",
            f"{goal[0]},{goal[1]}",
            *sensor_lines,
        ]
    )


#: Type alias used by the mission adapter for gadget dispatch.
ScenarioBuilder = Callable[..., dict[str, object]]

"""Deterministic figure generation for the ELEKTRA mission.

Renders the concept figures into ``output/figures/`` using a fixed, headless
Matplotlib style. All figures are derived from the same deterministic models
the mission executes, so a figure is always a faithful reproduction of the
current model outputs. No random draws, no wall-clock dependence.

Figures:

* ``pipeline_network.png`` — the oil-pipeline security graph with flow and
  choke points highlighted;
* ``submarine_detection.png`` — the passive-sonar risk field with naive vs.
  least-risk evasion routes overlaid;
* ``hostage_dynamics.png`` — the Stockholm-syndrome ODE time series
  (fear / gratitude / identification / syndrome index);
* ``sensor_fusion_track.png`` — the Kalman-filter track of the hijacked
  submarine against the noisy fixes and the true trajectory.
"""

from __future__ import annotations

import os
import zlib
from pathlib import Path
from typing import cast

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from the_world_is_not_enough import (
    hostage_psychology,
    pipeline_security,
    sensor_fusion,
    sub_defense,
)

__all__ = [
    "figure_hostage_dynamics",
    "figure_pipeline_network",
    "figure_sensor_fusion_track",
    "figure_submarine_detection",
    "generate_all_figures",
]


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "font.size": 9,
        }
    )


def _stable_fraction(name: str, buckets: int = 100) -> float:
    """A process-independent fraction in ``[0, 1)`` derived from ``name``.

    ``hash(name)`` would be salted per process, so it cannot place a figure
    reproducibly; a CRC of the bytes can, and it scatters the same way.
    """
    return zlib.crc32(name.encode("utf-8")) % buckets / buckets


def figure_pipeline_network(
    network: pipeline_security.PipelineNetwork,
    analysis: dict[str, object],
    save_path: str | os.PathLike[str] = "output/figures/pipeline_network.png",
) -> Path:
    """Render the pipeline graph with edge flow width and choke-point emphasis."""
    _style()
    # Deterministic spring-like layout: assign x by BFS depth, y by index.
    from collections import deque

    adjacency: dict[str, list[str]] = {n: [] for n in network.nodes}
    for edge in network.edges:
        adjacency[edge.source].append(edge.target)

    depth: dict[str, int] = {network.source: 0}
    queue: deque[str] = deque([network.source])
    while queue:
        node = queue.popleft()
        for nxt in adjacency[node]:
            if nxt not in depth:
                depth[nxt] = depth[node] + 1
                queue.append(nxt)
    max_depth = max(depth.values())
    x = {node: depth[node] / max(1, max_depth) for node in network.nodes}
    # ``hash()`` on a str is salted per process (PYTHONHASHSEED), so laying the
    # nodes out with it made this figure differ on every run. The digest below is
    # the same scattered placement, reproducible across processes and machines;
    # tests/test_figures.py::TestProcessIndependentLayout pins that.
    y = {
        node: (
            0.5 if node in (network.source, network.sink) else _stable_fraction(node)
        )
        for node in network.nodes
    }

    criticality = cast("dict[str, float]", analysis["criticality"])
    fig, ax = plt.subplots(figsize=(9, 5))
    for edge in network.edges:
        crit = float(criticality[edge.id])
        lw = 1.5 + 4.0 * crit
        color = "#c0392b" if crit >= 0.5 else ("#2c6fbb" if edge.sensor else "#7fb3d5")
        ax.plot(
            [x[edge.source], x[edge.target]],
            [y[edge.source], y[edge.target]],
            lw=lw,
            color=color,
            zorder=1,
        )
    for node in network.nodes:
        color = "#e67e22" if node in (network.source, network.sink) else "#34495e"
        ax.scatter([x[node]], [y[node]], s=90, color=color, zorder=3)
        ax.annotate(
            node,
            (x[node], y[node]),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
        )
    ax.set_title(
        "Oil-pipeline security graph — choke points (red) and flow-criticality"
    )
    ax.set_xlabel("relative depth from origin")
    ax.set_ylabel("station index (layout)")
    fig.tight_layout()
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def figure_submarine_detection(
    risk,
    start: tuple[int, int],
    goal: tuple[int, int],
    save_path: str | os.PathLike[str] = "output/figures/submarine_detection.png",
) -> Path:
    """Render the detection-risk field and compare naive vs. least-risk routes."""
    _style()
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(risk, origin="lower", cmap="inferno", aspect="equal")
    fig.colorbar(im, ax=ax, label="detection probability")

    direct = sub_defense.straight_line_path(start, goal)
    dx = [p[0] for p in direct]
    dy = [p[1] for p in direct]
    ax.plot(dx, dy, "--", color="white", lw=2, label="naive line-of-sight")

    routed = sub_defense.dijkstra_evasion(risk, start, goal)
    rx = [p[0] for p in routed.path]
    ry = [p[1] for p in routed.path]
    ax.plot(rx, ry, color="lime", lw=2.5, label="least-risk route")

    ax.scatter([start[0]], [start[1]], color="cyan", s=70, zorder=5, label="start")
    ax.scatter([goal[0]], [goal[1]], color="magenta", s=70, zorder=5, label="goal")
    ax.set_title("Nuclear-submarine defense — passive-sonar risk field & evasion")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def figure_hostage_dynamics(
    result: hostage_psychology.HostageDynamicsResult,
    save_path: str | os.PathLike[str] = "output/figures/hostage_dynamics.png",
) -> Path:
    """Render the Stockholm-syndrome ODE time series (all four states + index)."""
    _style()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(result.days, result.fear, label="fear F", color="#c0392b")
    ax.plot(result.days, result.gratitude, label="gratitude G", color="#2980b9")
    ax.plot(
        result.days, result.identification, label="identification I", color="#8e44ad"
    )
    ax.plot(result.days, result.syndrome, label="syndrome index S", color="black", lw=2)
    ax.axhline(0.5, color="gray", ls=":", lw=1)
    ax.set_title("Hostage-psychology influence model — Stockholm-syndrome dynamics")
    ax.set_xlabel("days in captivity")
    ax.set_ylabel("state (0..1)")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="center right", fontsize=8)
    fig.tight_layout()
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def figure_sensor_fusion_track(
    truth: np.ndarray,
    measurements: np.ndarray,
    filtered: list[sensor_fusion.FilterStep],
    save_path: str | os.PathLike[str] = "output/figures/sensor_fusion_track.png",
) -> Path:
    """Render the Kalman track against the true trajectory and the raw fixes."""
    _style()
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(truth[:, 0], truth[:, 1], color="black", lw=2, label="true trajectory")
    ax.scatter(
        measurements[:, 0],
        measurements[:, 1],
        s=18,
        color="gray",
        alpha=0.7,
        label="noisy position fixes",
    )
    fx = [step.position[0] for step in filtered]
    fy = [step.position[1] for step in filtered]
    ax.plot(fx, fy, color="lime", lw=2, marker="o", ms=3, label="Kalman track")
    ax.set_title("Sensor fusion — Kalman tracking of the hijacked submarine")
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def generate_all_figures(
    output_dir: str | os.PathLike[str] = "output/figures",
) -> dict[str, Path]:
    """Generate all concept figures and return their absolute paths."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    network = pipeline_security.default_pipeline()
    analysis = pipeline_security.analyze_choke_points(network)
    fig1 = figure_pipeline_network(network, analysis, out / "pipeline_network.png")

    sensors = (
        sub_defense.Sensor(
            x=8,
            y=3,
            source_level=125.0,
            noise_level=78.0,
            absorption_db_per_km=0.5,
            detection_threshold_db=15.0,
        ),
        sub_defense.Sensor(
            x=3,
            y=9,
            source_level=125.0,
            noise_level=78.0,
            absorption_db_per_km=0.5,
            detection_threshold_db=15.0,
        ),
        sub_defense.Sensor(
            x=12,
            y=12,
            source_level=125.0,
            noise_level=78.0,
            absorption_db_per_km=0.5,
            detection_threshold_db=15.0,
        ),
    )
    risk = sub_defense.build_risk_map(16, sensors, 3000.0)
    fig2 = figure_submarine_detection(
        risk, (1, 1), (14, 14), out / "submarine_detection.png"
    )

    dynamics = hostage_psychology.integrate_dynamics()
    fig3 = figure_hostage_dynamics(dynamics, out / "hostage_dynamics.png")

    tracking = sensor_fusion.TrackConfig(seed=1999)
    truth, measurements = sensor_fusion.generate_track(tracking)
    filter_model = sensor_fusion.KalmanFilter(tracking, measurements[0])
    filtered = filter_model.run(measurements)
    fig4 = figure_sensor_fusion_track(
        truth, measurements, filtered, out / "sensor_fusion_track.png"
    )
    return {
        "pipeline_network": fig1,
        "submarine_detection": fig2,
        "hostage_dynamics": fig3,
        "sensor_fusion_track": fig4,
    }

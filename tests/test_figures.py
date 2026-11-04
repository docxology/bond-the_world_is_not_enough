"""In-process tests for deterministic figure generation (ELEKTRA).

Matplotlib is forced headless (Agg) in conftest; every figure is rendered to a
tmp directory and its PNG existence + non-empty size asserted. No mocks.

The last test crosses a process boundary on purpose: determinism that survives
only within one interpreter is what ``hash()`` on a string looked like.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from the_world_is_not_enough import figures as F
from the_world_is_not_enough import (
    hostage_psychology,
    pipeline_security,
    sensor_fusion,
    sub_defense,
)

ROOT = Path(__file__).resolve().parents[1]


class TestIndividualFigures:
    def test_pipeline_network(self, tmp_path: Path) -> None:
        network = pipeline_security.default_pipeline()
        analysis = pipeline_security.analyze_choke_points(network)
        path = F.figure_pipeline_network(network, analysis, tmp_path / "p.png")
        assert path.is_file()
        assert path.stat().st_size > 0

    def test_pipeline_network_with_a_revisited_node(self, tmp_path: Path) -> None:
        """Drive the BFS depth-layout 'already seen' arm with a diamond."""
        network = pipeline_security.PipelineNetwork(
            source="S",
            sink="T",
            edges=[
                pipeline_security.PipelineEdge("S", "A", 5.0),
                pipeline_security.PipelineEdge("S", "B", 5.0),
                pipeline_security.PipelineEdge("A", "C", 5.0),
                pipeline_security.PipelineEdge("B", "C", 5.0),
                pipeline_security.PipelineEdge("C", "T", 10.0),
            ],
        )
        analysis = pipeline_security.analyze_choke_points(network)
        path = F.figure_pipeline_network(network, analysis, tmp_path / "diamond.png")
        assert path.is_file()
        assert path.stat().st_size > 0

    def test_submarine_detection(self, tmp_path: Path) -> None:
        sensors = tuple(
            sub_defense.Sensor(
                x=8,
                y=3,
                source_level=125.0,
                noise_level=78.0,
                absorption_db_per_km=0.5,
                detection_threshold_db=15.0,
            )
            for _ in range(1)
        ) + (sub_defense.Sensor(x=3, y=9, source_level=125.0, noise_level=78.0),)
        risk = sub_defense.build_risk_map(12, sensors, 3000.0)
        path = F.figure_submarine_detection(risk, (2, 2), (10, 10), tmp_path / "s.png")
        assert path.is_file()
        assert path.stat().st_size > 0

    def test_hostage_dynamics(self, tmp_path: Path) -> None:
        result = hostage_psychology.integrate_dynamics()
        path = F.figure_hostage_dynamics(result, tmp_path / "h.png")
        assert path.is_file()
        assert path.stat().st_size > 0


class TestGenerateAllFigures:
    def test_writes_all_four(self, tmp_path: Path) -> None:
        out = F.generate_all_figures(tmp_path)
        assert set(out) == {
            "pipeline_network",
            "submarine_detection",
            "hostage_dynamics",
            "sensor_fusion_track",
        }
        for path in out.values():
            assert path.is_file()
            assert path.stat().st_size > 0

    def test_output_dir_created(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        F.generate_all_figures(nested)
        assert nested.is_dir()
        assert (nested / "pipeline_network.png").is_file()

    def test_sensor_fusion_track(self, tmp_path: Path) -> None:
        tracking = sensor_fusion.TrackConfig(seed=7)
        truth, measurements = sensor_fusion.generate_track(tracking)
        model = sensor_fusion.KalmanFilter(tracking, measurements[0])
        filtered = model.run(measurements)
        path = F.figure_sensor_fusion_track(
            truth, measurements, filtered, tmp_path / "sf.png"
        )
        assert path.is_file()
        assert path.stat().st_size > 0


class TestProcessIndependentLayout:
    """The figure bytes must not depend on the interpreter's string-hash salt.

    ``PYTHONHASHSEED`` randomizes ``hash()`` on strings once per process, so a
    layout built from ``hash(node)`` produced different PNGs on every run while
    every in-process assertion stayed green. Two subprocesses started with
    different seeds must write byte-identical figures.
    """

    @staticmethod
    def _render(out_dir: Path, hashseed: str) -> dict[str, bytes]:
        env = dict(os.environ, PYTHONHASHSEED=hashseed)
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_figures.py"),
                "--output-dir",
                str(out_dir),
            ],
            check=True,
            capture_output=True,
            env=env,
        )
        return {p.name: p.read_bytes() for p in sorted(out_dir.glob("*.png"))}

    def test_figures_are_identical_under_two_hash_seeds(self, tmp_path: Path) -> None:
        first = self._render(tmp_path / "seed0", "0")
        second = self._render(tmp_path / "seed12345", "12345")
        assert set(first) == set(second)
        assert first == second, "figure bytes moved with PYTHONHASHSEED"

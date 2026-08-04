"""In-process tests for deterministic figure generation (ELEKTRA).

Matplotlib is forced headless (Agg) in conftest; every figure is rendered to a
tmp directory and its PNG existence + non-empty size asserted. No mocks.
"""

from __future__ import annotations

from pathlib import Path

from the_world_is_not_enough import figures as F
from the_world_is_not_enough import hostage_psychology, pipeline_security, sub_defense


class TestIndividualFigures:
    def test_pipeline_network(self, tmp_path: Path) -> None:
        network = pipeline_security.default_pipeline()
        analysis = pipeline_security.analyze_choke_points(network)
        path = F.figure_pipeline_network(network, analysis, tmp_path / "p.png")
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
    def test_writes_all_three(self, tmp_path: Path) -> None:
        out = F.generate_all_figures(tmp_path)
        assert set(out) == {
            "pipeline_network",
            "submarine_detection",
            "hostage_dynamics",
        }
        for path in out.values():
            assert path.is_file()
            assert path.stat().st_size > 0

    def test_output_dir_created(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        F.generate_all_figures(nested)
        assert nested.is_dir()
        assert (nested / "pipeline_network.png").is_file()

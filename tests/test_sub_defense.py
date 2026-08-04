"""Real-data tests for nuclear-submarine defense (ELEKTRA pillar 2).

Zero mocks: asserts the passive-sonar equation, normal-CDF detection link,
Dijkstra evasion routing, and bearing triangulation against known analytic
and hand-constructed values.
"""

from __future__ import annotations

import numpy as np
import pytest

from the_world_is_not_enough import sub_defense as S


class TestNormalCdf:
    def test_known_values(self) -> None:
        assert S.normal_cdf(0.0) == pytest.approx(0.5)
        assert S.normal_cdf(1.96) == pytest.approx(0.9750, abs=1e-3)
        assert S.normal_cdf(-1.96) == pytest.approx(0.0250, abs=1e-3)

    def test_monotonic(self) -> None:
        assert S.normal_cdf(0.0) < S.normal_cdf(1.0) < S.normal_cdf(2.0)

    def test_array_input(self) -> None:
        out = S.normal_cdf(np.array([-1.0, 0.0, 1.0]))
        assert out.shape == (3,)
        assert float(out[0]) < float(out[1]) < float(out[2])


class TestPassiveSonarSnr:
    def test_negative_range_raises(self) -> None:
        with pytest.raises(ValueError):
            S.passive_sonar_snr(150.0, -5.0)

    def test_reference_range_value(self) -> None:
        # at r=1000 m, TL = 20*log10(1) + 0.05*1 = 0.05 -> SNR = SL - 0.05 - NL + DI
        snr = S.passive_sonar_snr(
            150.0, 1000.0, absorption_db_per_km=0.05, noise_level=65.0
        )
        assert snr == pytest.approx(150.0 - 0.05 - 65.0)

    def test_monotone_decreasing(self) -> None:
        assert S.passive_sonar_snr(150.0, 1000.0) > S.passive_sonar_snr(150.0, 10_000.0)

    def test_array_input(self) -> None:
        out = S.passive_sonar_snr(150.0, np.array([1000.0, 10_000.0]))
        assert out.shape == (2,)
        assert float(out[0]) > float(out[1])


class TestDetectionProbability:
    def test_bounds(self) -> None:
        for snr in (-100.0, -10.0, 0.0, 10.0, 30.0, 100.0):
            p = S.detection_probability(snr)
            assert 0.0 <= p <= 1.0

    def test_threshold_is_fifty_percent(self) -> None:
        # SNR == DT -> Phi(0) = 0.5
        assert S.detection_probability(
            15.0, detection_threshold_db=15.0
        ) == pytest.approx(0.5)

    def test_increases_with_snr(self) -> None:
        assert S.detection_probability(20.0) > S.detection_probability(5.0)

    def test_invalid_threshold(self) -> None:
        with pytest.raises(ValueError):
            S.detection_probability(10.0, detection_threshold_db=-1.0)

    def test_invalid_sigma(self) -> None:
        with pytest.raises(ValueError):
            S.detection_probability(10.0, sigma_db=0.0)


class TestSensor:
    def test_invalid_coordinates(self) -> None:
        with pytest.raises(ValueError):
            S.Sensor(x=-1, y=3)
        with pytest.raises(ValueError):
            S.Sensor(x=3, y=-1)

    def test_invalid_source_level(self) -> None:
        with pytest.raises(ValueError):
            S.Sensor(x=1, y=1, source_level=-5.0)


class TestBuildRiskMap:
    def _sensors(self) -> tuple[S.Sensor, ...]:
        return (
            S.Sensor(x=8, y=3, source_level=125.0, noise_level=78.0),
            S.Sensor(x=3, y=9, source_level=125.0, noise_level=78.0),
            S.Sensor(x=12, y=12, source_level=125.0, noise_level=78.0),
        )

    def test_invalid_grid(self) -> None:
        with pytest.raises(ValueError):
            S.build_risk_map(1, ())

    def test_shape_and_bounds(self) -> None:
        risk = S.build_risk_map(16, self._sensors(), 3000.0)
        assert risk.shape == (16, 16)
        assert float(risk.min()) >= 0.0
        assert float(risk.max()) <= 1.0

    def test_risk_higher_near_sensor(self) -> None:
        risk = S.build_risk_map(16, self._sensors(), 3000.0)
        # a cell on top of a sensor is detected almost surely
        assert float(risk[3, 8]) > float(risk[0, 0])

    def test_deterministic(self) -> None:
        a = S.build_risk_map(16, self._sensors(), 3000.0)
        b = S.build_risk_map(16, self._sensors(), 3000.0)
        np.testing.assert_array_equal(a, b)


class TestStraightLinePath:
    def test_same_point(self) -> None:
        assert S.straight_line_path((3, 3), (3, 3)) == ((3, 3),)

    def test_monotone_reaches_goal(self) -> None:
        start, goal = (1, 1), (14, 14)
        path = S.straight_line_path(start, goal)
        assert path[0] == start
        assert path[-1] == goal
        # 4-connected and monotone: only single-step axis moves
        for a, b in zip(path, path[1:]):  # noqa: RUF007 - multi-step tuple pairwise
            assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


class TestDijkstraEvasion:
    def test_same_point(self) -> None:
        risk = np.zeros((5, 5))
        res = S.dijkstra_evasion(risk, (2, 2), (2, 2))
        assert res.path == ((2, 2),)
        assert res.cumulative_exposure == pytest.approx(0.0)
        assert res.path_length == 1

    def test_out_of_bounds(self) -> None:
        risk = np.zeros((4, 4))
        with pytest.raises(ValueError):
            S.dijkstra_evasion(risk, (-1, 0), (2, 2))
        with pytest.raises(ValueError):
            S.dijkstra_evasion(risk, (0, 0), (9, 9))

    def test_non_square_raises(self) -> None:
        with pytest.raises(ValueError):
            S.dijkstra_evasion(np.zeros((3, 4)), (0, 0), (2, 2))

    def test_uniform_grid_cost_is_manhattan(self) -> None:
        r = 0.1
        risk = np.full((5, 5), r)
        res = S.dijkstra_evasion(risk, (0, 0), (2, 2))
        # Manhattan distance = 4 steps; cost excludes start, includes goal
        assert res.cumulative_exposure == pytest.approx(4 * r)
        assert res.path_length == 5

    def test_detours_around_high_risk(self) -> None:
        # a wall of high risk on the direct route forces a longer safe path
        risk = np.zeros((5, 5))
        risk[1, 1:4] = 1.0  # high-risk horizontal wall
        risk[2, 1:4] = 1.0
        res = S.dijkstra_evasion(risk, (0, 2), (4, 2))
        # path must not pass through a wall cell
        assert all(risk[y, x] < 0.5 for x, y in res.path)
        assert res.cumulative_exposure == pytest.approx(0.0)

    def test_deterministic(self) -> None:
        risk = np.random.default_rng(0).random((6, 6)) * 0.5
        a = S.dijkstra_evasion(risk, (0, 0), (5, 5))
        b = S.dijkstra_evasion(risk, (0, 0), (5, 5))
        assert a.cumulative_exposure == pytest.approx(b.cumulative_exposure)
        assert a.path == b.path


class TestEvasionAnalysis:
    def test_reduction_nonnegative(self) -> None:
        risk = np.random.default_rng(7).random((10, 10)) * 0.6
        r = S.evasion_analysis(risk, (0, 0), (9, 9))
        assert r["exposure_reduction"] >= -1e-12
        assert r["exposure_reduction"] <= 1.0
        assert r["optimal_exposure"] <= r["naive_exposure"] + 1e-12
        assert r["naive_path_length"] >= 1
        assert r["optimal_path_length"] >= 1

    def test_deterministic(self) -> None:
        risk = np.random.default_rng(3).random((6, 6)) * 0.5
        assert S.evasion_analysis(risk, (0, 0), (5, 5)) == S.evasion_analysis(
            risk, (0, 0), (5, 5)
        )

    def test_zero_exposure_risk_map(self) -> None:
        risk = np.zeros((4, 4))
        r = S.evasion_analysis(risk, (0, 0), (3, 3))
        assert r["naive_exposure"] == pytest.approx(0.0)
        assert r["optimal_exposure"] == pytest.approx(0.0)
        assert r["exposure_reduction"] == pytest.approx(0.0)


class TestTriangulate:
    def test_perpendicular_bearings(self) -> None:
        fix = S.triangulate_bearings((0.0, 0.0), 0.0, (0.0, 10.0), 90.0)
        assert fix is not None
        assert fix[0] == pytest.approx(0.0, abs=1e-6)
        assert fix[1] == pytest.approx(0.0, abs=1e-6)

    def test_parallel_returns_none(self) -> None:
        assert S.triangulate_bearings((0.0, 0.0), 0.0, (1.0, 2.0), 0.0) is None

    def test_bad_position(self) -> None:
        with pytest.raises(ValueError):
            S.triangulate_bearings((0.0, 0.0, 1.0), 0.0, (0.0, 10.0), 90.0)  # type: ignore[arg-type]


class TestScenarioFingerprint:
    def test_stable_and_distinct(self) -> None:
        s1 = (S.Sensor(x=1, y=1),)
        fp = S.scenario_fingerprint(16, s1, (0, 0), (3, 3))
        assert fp == S.scenario_fingerprint(16, s1, (0, 0), (3, 3))
        s2 = (S.Sensor(x=2, y=2),)
        assert fp != S.scenario_fingerprint(16, s2, (0, 0), (3, 3))


class TestEvasionResult:
    def test_as_dict(self) -> None:
        res = S.EvasionResult(
            path=((0, 0), (1, 0)), cumulative_exposure=0.5, path_length=2
        )
        d = res.as_dict()
        assert d["path"] == [[0, 0], [1, 0]]
        assert d["cumulative_exposure"] == 0.5
        assert d["path_length"] == 2

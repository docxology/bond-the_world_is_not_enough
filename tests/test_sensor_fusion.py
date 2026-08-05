"""Real-data tests for the sensor-fusion Kalman tracking model (ELEKTRA).

Zero mocks: asserts constant-velocity truth generation, Kalman predict/update,
RMSE metrics, and deterministic convergence against the hand-built filter.
"""

from __future__ import annotations

import numpy as np
import pytest

from the_world_is_not_enough import sensor_fusion as SF


class TestTrackConfig:
    def test_defaults(self) -> None:
        config = SF.TrackConfig()
        assert config.steps == 20
        assert config.measurement_noise == 2.0

    def test_nonpositive_dt(self) -> None:
        with pytest.raises(ValueError):
            SF.TrackConfig(dt=0.0)

    def test_small_steps(self) -> None:
        with pytest.raises(ValueError):
            SF.TrackConfig(steps=1)

    def test_negative_process_noise(self) -> None:
        with pytest.raises(ValueError):
            SF.TrackConfig(process_noise=-0.1)

    def test_nonpositive_measurement_noise(self) -> None:
        with pytest.raises(ValueError):
            SF.TrackConfig(measurement_noise=0.0)

    def test_bad_seed(self) -> None:
        with pytest.raises(ValueError):
            SF.TrackConfig(seed=-1)

    def test_bad_initial_state(self) -> None:
        with pytest.raises(ValueError):
            SF.TrackConfig(initial_state=(0.0, 0.0, 1.0))  # type: ignore[arg-type]


class TestGenerateTrack:
    def test_shapes(self) -> None:
        truth, measurements = SF.generate_track(SF.TrackConfig())
        assert truth.shape == (20, 4)
        assert measurements.shape == (20, 2)

    def test_deterministic(self) -> None:
        config = SF.TrackConfig()
        t1, m1 = SF.generate_track(config)
        t2, m2 = SF.generate_track(config)
        np.testing.assert_array_equal(t1, t2)
        np.testing.assert_array_equal(m1, m2)

    def test_linear_motion(self) -> None:
        config = SF.TrackConfig(initial_state=(0.0, 0.0, 2.0, 1.0), steps=5)
        truth, _ = SF.generate_track(config)
        # constant velocity: position at step k = position0 + k*v*dt
        assert truth[4, 0] == pytest.approx(8.0)  # 2.0 * 4 * 1.0
        assert truth[4, 1] == pytest.approx(4.0)

    def test_last_sample_matches_truth_plus_noise_scale(self) -> None:
        config = SF.TrackConfig(seed=3)
        truth, measurements = SF.generate_track(config)
        error = np.linalg.norm(measurements[-1] - truth[-1, :2])
        assert error < 5 * config.measurement_noise


class TestKalmanFilter:
    def _run_local(self, config: SF.TrackConfig):
        truth, measurements = SF.generate_track(config)
        model = SF.KalmanFilter(config, measurements[0])
        steps = model.run(measurements)
        return truth, measurements, model, steps

    def test_predict_update_finite_covariance(self) -> None:
        config = SF.TrackConfig()
        _, _, _, steps = self._run_local(config)
        for step in steps:
            assert np.isfinite(step.covariance_trace)
        # filter refines: clip step should have lower covariance than the start
        assert steps[-1].covariance_trace <= steps[0].covariance_trace + 1e-9

    def test_position_and_velocity(self) -> None:
        config = SF.TrackConfig(initial_state=(10.0, 20.0, 3.0, 2.0))
        _, _, model, _ = self._run_local(config)
        px, py = model.position()
        vx, vy = model.velocity()
        assert isinstance(px, float) and isinstance(py, float)
        assert vx > 0 and vy > 0  # target moving in +x/+y

    def test_run_bad_measurements(self) -> None:
        config = SF.TrackConfig()
        _, measurements, model, _ = self._run_local(config)
        bad = measurements[:1]  # (1, 2) is allowed
        _ = model.run(bad)  # no error
        with pytest.raises(ValueError):
            model.run(np.zeros((3, 3)))


class TestTrackRms:
    def test_zero_when_perfect(self) -> None:
        truth = np.zeros((5, 4))
        filtered = [SF.FilterStep(float(i), (0.0, 0.0), 0.0, 0.0) for i in range(5)]
        assert SF.track_rmse(filtered, truth) == pytest.approx(0.0)

    def test_array_baseline(self) -> None:
        truth = np.zeros((4, 4))
        array_track = np.array(
            [
                [0.0, 0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0],
            ]
        )
        # distances: 0, 1, 1, 0 -> rmse = sqrt((1+1+0+0)/4) = sqrt(0.5)
        assert SF.track_rmse(array_track, truth) == pytest.approx(
            np.sqrt(0.5), abs=1e-6
        )

    def test_empty_truth_raises(self) -> None:
        with pytest.raises(ValueError):
            SF.track_rmse([], np.zeros((0, 4)))


class TestRunTracking:
    def test_filter_beats_raw_measurements(self) -> None:
        result = SF.run_tracking()
        assert result["filter_rmse"] < result["measurement_rmse"]
        assert result["converged"] is True
        assert result["filter_gain"] > 0.0

    def test_measured_values(self) -> None:
        result = SF.run_tracking()
        assert result["filter_rmse"] == pytest.approx(1.7758, abs=1e-3)
        assert result["measurement_rmse"] == pytest.approx(2.9118, abs=1e-3)
        assert result["final_position_error"] == pytest.approx(0.8799, abs=5e-2)

    def test_deterministic(self) -> None:
        assert SF.run_tracking() == SF.run_tracking()

    def test_low_noise_converges_better(self) -> None:
        config = SF.TrackConfig(measurement_noise=0.5)
        result = SF.run_tracking(config)
        assert result["converged"] is True
        assert result["filter_rmse"] < result["measurement_rmse"]


class TestFilterStep:
    def test_as_dict(self) -> None:
        step = SF.FilterStep(
            time=1.0, position=(3.0, 4.0), innovation_norm=0.5, covariance_trace=2.0
        )
        d = step.as_dict()
        assert d["position"] == [3.0, 4.0]
        assert d["time"] == 1.0

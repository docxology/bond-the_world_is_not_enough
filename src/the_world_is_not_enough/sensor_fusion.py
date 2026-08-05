"""Sensor fusion: Kalman filtering for tracking the hijacked submarine.

ELEKTRA's sixth pillar deepens the submarine-defense pillar from a static
risk field into a recursive estimation problem: the stolen *King William* is
tracked through the patrol box from noisy position fixes (sonar/ESM bearings
fused into contacts), and the filter's state — position and velocity — drives
interception geometry.

The mathematics is the classical linear Kalman filter [@kalman]:

* **Predict** — :math:`\\hat{x}_{k|k-1} = F\\,\\hat{x}_{k-1}`,
  :math:`P_{k|k-1} = F P_{k-1} F^T + Q` for a constant-velocity model;
* **Update** — :math:`K = P H^T (H P H^T + R)^{-1}`,
  :math:`\\hat{x}_k = \\hat{x}_{k|k-1} + K\\,(z_k - H\\hat{x}_{k|k-1})`,
  :math:`P_k = (I - K H) P_{k|k-1}`.

Measurement noise is drawn from a fixed-seed generator so the whole track is
byte-reproducible. The headline metric is the filter's position RMSE against
the true track, compared with the raw-measurement RMSE to show the gain of
fusion. (Bearing-only tracking from a stationary observer is scale-ambiguous;
the model therefore fuses noisy *position* fixes, which is the convergent
headline, and documents the limitation.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = [
    "FilterStep",
    "KalmanFilter",
    "TrackConfig",
    "generate_track",
    "run_tracking",
    "track_rmse",
]


@dataclass(frozen=True)
class TrackConfig:
    """Deterministic scenario for the constant-velocity tracking problem."""

    dt: float = 1.0
    steps: int = 20
    process_noise: float = 0.1
    measurement_noise: float = 2.0
    seed: int = 1999
    initial_state: tuple[float, float, float, float] = (0.0, 0.0, 1.5, 1.0)

    def __post_init__(self) -> None:
        if self.dt <= 0:
            raise ValueError("TrackConfig.dt must be positive")
        if (
            isinstance(self.steps, bool)
            or not isinstance(self.steps, int)
            or self.steps < 2
        ):
            raise ValueError("TrackConfig.steps must be an int >= 2")
        if self.process_noise < 0:
            raise ValueError("TrackConfig.process_noise must be non-negative")
        if self.measurement_noise <= 0:
            raise ValueError("TrackConfig.measurement_noise must be positive")
        if (
            isinstance(self.seed, bool)
            or not isinstance(self.seed, int)
            or self.seed < 0
        ):
            raise ValueError("TrackConfig.seed must be a non-negative int")
        if len(self.initial_state) != 4:
            raise ValueError("TrackConfig.initial_state must be (x, y, vx, vy)")


@dataclass(frozen=True)
class FilterStep:
    """One filtered time step: position, innovation norm, and covariance scale."""

    time: float
    position: tuple[float, float]
    innovation_norm: float
    covariance_trace: float

    def as_dict(self) -> dict[str, object]:
        return {
            "time": self.time,
            "position": [self.position[0], self.position[1]],
            "innovation_norm": self.innovation_norm,
            "covariance_trace": self.covariance_trace,
        }


def generate_track(config: TrackConfig) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic truth + noisy measurements for the scenario.

    Returns ``(truth, measurements)`` arrays shaped ``(steps, 4)`` (x, y, vx,
    vy) and ``(steps, 2)`` (x, y). Motion is constant-velocity; the noise
    comes from ``numpy.random.default_rng(config.seed)``.
    """
    rng = np.random.default_rng(config.seed)
    x0, y0, vx, vy = config.initial_state
    truth = np.zeros((config.steps, 4), dtype=np.float64)
    measurements = np.zeros((config.steps, 2), dtype=np.float64)
    x, y = x0, y0
    for step in range(config.steps):
        truth[step] = (x, y, vx, vy)
        measurements[step] = (
            x + float(rng.normal(0.0, config.measurement_noise)),
            y + float(rng.normal(0.0, config.measurement_noise)),
        )
        x += vx * config.dt
        y += vy * config.dt
    return truth, measurements


class KalmanFilter:
    """Constant-velocity linear Kalman filter over noisy position fixes."""

    def __init__(self, config: TrackConfig, first_measurement: np.ndarray) -> None:
        self.config = config
        dt = config.dt
        self._f: np.ndarray = np.array(
            [
                [1.0, 0.0, dt, 0.0],
                [0.0, 1.0, 0.0, dt],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
        self._h: np.ndarray = np.array(
            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
            dtype=np.float64,
        )
        # process-noise coupling: white acceleration -> velocity and position
        g: np.ndarray = np.array(
            [
                [0.5 * dt * dt, 0.0],
                [0.0, 0.5 * dt * dt],
                [dt, 0.0],
                [0.0, dt],
            ],
            dtype=np.float64,
        )
        self._q = config.process_noise * (g @ g.T)
        self._r = config.measurement_noise**2 * np.eye(2)
        self._x: np.ndarray = np.zeros(4, dtype=np.float64)
        self._x[0] = float(first_measurement[0])
        self._x[1] = float(first_measurement[1])
        self._x[2] = config.initial_state[2]
        self._x[3] = config.initial_state[3]
        self._p: np.ndarray = np.diag(
            [config.measurement_noise**2, config.measurement_noise**2, 10.0, 10.0]
        )

    def predict(self) -> None:
        """Time update: propagate state and covariance."""
        self._x = self._f @ self._x
        self._p = self._f @ self._p @ self._f.T + self._q

    def update(self, measurement: np.ndarray) -> float:
        """Measurement update with a position fix; returns the innovation norm."""
        innovation = measurement - self._h @ self._x
        s = self._h @ self._p @ self._h.T + self._r
        gain = self._p @ self._h.T @ np.linalg.inv(s)
        self._x = self._x + gain @ innovation
        self._p = (np.eye(4) - gain @ self._h) @ self._p
        innovation_norm = float(np.linalg.norm(innovation))
        return innovation_norm

    def position(self) -> tuple[float, float]:
        """Current filtered position ``(x, y)``."""
        return (float(self._x[0]), float(self._x[1]))

    def velocity(self) -> tuple[float, float]:
        """Current filtered velocity ``(vx, vy)``."""
        return (float(self._x[2]), float(self._x[3]))

    def covariance_trace(self) -> float:
        """Trace of the state covariance (overall uncertainty)."""
        return float(np.trace(self._p))

    def run(self, measurements: np.ndarray) -> list[FilterStep]:
        """Filter the full measurement sequence (predict between fixes)."""
        if measurements.shape[0] < 1 or measurements.shape[1] != 2:
            raise ValueError("measurements must be an (n, 2) position sequence")
        steps: list[FilterStep] = []
        for index in range(measurements.shape[0]):
            if index > 0:
                self.predict()
            innovation = self.update(measurements[index])
            steps.append(
                FilterStep(
                    time=float(index * self.config.dt),
                    position=self.position(),
                    innovation_norm=innovation,
                    covariance_trace=self.covariance_trace(),
                )
            )
        return steps


def track_rmse(
    filtered: list[FilterStep] | np.ndarray,
    truth: np.ndarray,
) -> float:
    """Root-mean-square position error between a track and the truth.

    ``filtered`` may be a list of :class:`FilterStep` or an ``(n, 4)`` array
    of state vectors (used for the raw-measurement baseline).
    """
    n = truth.shape[0]
    if n == 0:
        raise ValueError("truth must contain at least one sample")
    if isinstance(filtered, list):
        errors = [
            (step.position[0] - float(truth[i, 0])) ** 2
            + (step.position[1] - float(truth[i, 1])) ** 2
            for i, step in enumerate(filtered)
        ]
    else:
        errors = [
            (float(filtered[i, 0]) - float(truth[i, 0])) ** 2
            + (float(filtered[i, 1]) - float(truth[i, 1])) ** 2
            for i in range(n)
        ]
    return float(np.sqrt(float(np.mean(errors))))


def run_tracking(config: TrackConfig | None = None) -> dict[str, Any]:
    """Run the full deterministic tracking scenario.

    Generates truth and noisy fixes, filters them, and reports the position
    RMSE of the filter and of the raw measurements (the no-fusion baseline),
    the final position error, and whether the filter converged (final error
    below the measurement-noise level).
    """
    config = config or TrackConfig()
    truth, measurements = generate_track(config)
    filter_model = KalmanFilter(config, measurements[0])
    filtered = filter_model.run(measurements)
    filter_rmse = track_rmse(filtered, truth)
    measurement_rmse = track_rmse(measurements, truth)
    final_error = float(
        np.hypot(
            filtered[-1].position[0] - float(truth[-1, 0]),
            filtered[-1].position[1] - float(truth[-1, 1]),
        )
    )
    return {
        "filter_rmse": filter_rmse,
        "measurement_rmse": measurement_rmse,
        "final_position_error": final_error,
        "converged": final_error < config.measurement_noise,
        "filter_gain": (measurement_rmse - filter_rmse) / measurement_rmse
        if measurement_rmse > 0
        else 0.0,
    }

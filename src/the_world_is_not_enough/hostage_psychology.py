"""Hostage-psychology influence model: Stockholm-syndrome dynamics.

ELEKTRA's third pillar models the captive–captor psychological dynamics that
underpin Stockholm syndrome — the emotional bond a captive can form with a
captor. It is a deterministic, phenomenological system of ordinary
differential equations over four bounded states:

* ``fear`` (F) — the captive's fear of the captor, driven up by the perceived
  threat ``T(t)`` and decaying on its own;
* ``gratitude`` (G) — gratitude for small kindnesses ``K(t)`` (the classic
  "small kindness" condition), decaying over time;
* ``identification`` (I) — identification with / emotional investment in the
  captor, rising with gratitude and suppressed by fear; this is the syndrome
  core;
* ``threat`` (T) — a time-varying external input (captivity threat schedule),
  high early and decaying as the situation normalizes.

The composite **syndrome index** ``S = clamp((2*I + G - F) / 3)`` in [0, 1]
summarizes the state; mission-relevant outcomes (final index, peak, onset day
where S first crosses 0.5, and an influence ratio ``I/(F+G+I+eps)``) are
reported for negotiation-force guidance. Integration uses a fixed-step
RK4 method over a deterministic time grid — no random draws, exact
reproducibility.

The model is grounded in the qualitative conditions catalogued in the
clinical/forensic literature (perceived threat, small kindnesses, isolation,
identification; see manuscript references, e.g. Namnyak et al. 2008) and is
documented as a phenomenological decision-support model, not a clinical
diagnostic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = [
    "DynamicsParams",
    "HostageDynamicsResult",
    "KindnessEvent",
    "derivatives",
    "integrate_dynamics",
    "rk4_step",
    "syndrome_index",
    "threat_schedule",
]


@dataclass(frozen=True)
class DynamicsParams:
    """Rate parameters of the hostage-psychology ODE system.

    All six rates are positive; the model is stable within [0, 1] state bounds
    by construction of the saturating terms.
    """

    fear_decay: float = 0.12  # a  : fear self-decay
    threat_sensitivity: float = 0.30  # b  : threat -> fear
    kindness_gain: float = 0.65  # c  : kindness -> gratitude
    gratitude_decay: float = 0.05  # d  : gratitude decay
    ident_gain: float = 0.50  # e  : gratitude -> identification
    fear_suppress: float = 0.15  # f  : fear suppresses identification
    threat_initial: float = 0.75  # T0 : captivity threat at t=0
    threat_decay: float = 0.18  # lambda : threat decay rate
    threat_floor: float = 0.12  # residual threat floor

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if value < 0:
                raise ValueError(f"DynamicsParams.{name} must be non-negative")


@dataclass(frozen=True)
class KindnessEvent:
    """A single small-kindness act on a given day."""

    day: float
    magnitude: float  # 0..1, scaled into gratitude

    def __post_init__(self) -> None:
        if self.day < 0:
            raise ValueError("KindnessEvent.day must be non-negative")
        if not 0.0 <= self.magnitude <= 1.0:
            raise ValueError("KindnessEvent.magnitude must be in [0, 1]")


def threat_schedule(
    params: DynamicsParams,
    t: float,
) -> float:
    """Time-varying captivity threat: exponential decay to a residual floor."""
    return params.threat_floor + params.threat_initial * math.exp(
        -params.threat_decay * max(t, 0.0)
    )


def _kindness_input(
    events: tuple[KindnessEvent, ...], t: float, bandwidth: float = 0.5
) -> float:
    """Gaussian-smoothed kindness impulse train over days (SD = ``bandwidth``)."""
    total = 0.0
    for ev in events:
        d = t - ev.day
        total += (
            ev.magnitude
            * math.exp(-0.5 * (d / bandwidth) ** 2)
            / (bandwidth * math.sqrt(2.0 * math.pi))
        )
    return total


def derivatives(
    state: tuple[float, float, float],
    params: DynamicsParams,
    threat: float,
    kindness: float,
) -> tuple[float, float, float]:
    """Right-hand side of the ODE system, ``(dF/dt, dG/dt, dI/dt)``.

    State = (fear, gratitude, identification), each a bounded fraction of 1.
    """
    fear, gratitude, identification = state
    dF = -params.fear_decay * fear + params.threat_sensitivity * threat * (1.0 - fear)
    dG = (
        params.kindness_gain * kindness * (1.0 - gratitude)
        - params.gratitude_decay * gratitude
    )
    dI = (
        params.ident_gain * gratitude * (1.0 - identification)
        - params.fear_suppress * fear * identification
    )
    return (dF, dG, dI)


def rk4_step(
    state: tuple[float, float, float],
    params: DynamicsParams,
    threat: float,
    kindness: float,
    dt: float,
) -> tuple[float, float, float]:
    """One fixed-step classical Runge–Kutta (RK4) integration step."""
    k1 = derivatives(state, params, threat, kindness)
    mid = _add_scaled(state, k1, dt * 0.5)
    k2 = derivatives(mid, params, threat, kindness)
    mid2 = _add_scaled(state, k2, dt * 0.5)
    k3 = derivatives(mid2, params, threat, kindness)
    end = _add_scaled(state, k3, dt)
    k4 = derivatives(end, params, threat, kindness)
    result = tuple(
        state[i] + (dt / 6.0) * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i])
        for i in range(3)
    )
    return (result[0], result[1], result[2])


def _add_scaled(
    state: tuple[float, float, float],
    slope: tuple[float, float, float],
    scale: float,
) -> tuple[float, float, float]:
    return (
        state[0] + scale * slope[0],
        state[1] + scale * slope[1],
        state[2] + scale * slope[2],
    )


def syndrome_index(state: tuple[float, float, float]) -> float:
    """Composite syndrome index in [0, 1]: ``(2*I + G - F) / 3`` clamped."""
    fear, gratitude, identification = state
    raw = (2.0 * identification + gratitude - fear) / 3.0
    return min(1.0, max(0.0, raw))


@dataclass
class HostageDynamicsResult:
    """Full deterministic output of the hostage-psychology integration."""

    days: list[float]
    fear: list[float]
    gratitude: list[float]
    identification: list[float]
    syndrome: list[float]
    params: DynamicsParams = field(default_factory=DynamicsParams)
    final_syndrome: float = 0.0
    peak_syndrome: float = 0.0
    peak_day: float = 0.0
    onset_day: float | None = None
    influence_ratio: float = 0.0

    def as_dict(self) -> dict[str, object]:
        """JSON-serializable summary of the integration (no raw time series)."""
        return {
            "days_simulated": self.days[-1] if self.days else 0.0,
            "final_syndrome": self.final_syndrome,
            "peak_syndrome": self.peak_syndrome,
            "peak_day": self.peak_day,
            "onset_day": self.onset_day,
            "influence_ratio": self.influence_ratio,
            "identification_final": self.identification[-1]
            if self.identification
            else 0.0,
            "gratitude_final": self.gratitude[-1] if self.gratitude else 0.0,
            "fear_final": self.fear[-1] if self.fear else 0.0,
        }


def integrate_dynamics(
    *,
    days: float = 30.0,
    dt: float = 0.25,
    params: DynamicsParams | None = None,
    events: tuple[KindnessEvent, ...] = (
        KindnessEvent(day=2.0, magnitude=0.7),
        KindnessEvent(day=5.0, magnitude=0.6),
        KindnessEvent(day=9.0, magnitude=0.5),
        KindnessEvent(day=14.0, magnitude=0.4),
    ),
    initial_state: tuple[float, float, float] = (0.7, 0.0, 0.02),
    onset_threshold: float = 0.5,
) -> HostageDynamicsResult:
    """Integrate the ODE system from ``t=0`` to ``t=days`` with step ``dt``.

    Deterministic: fixed grid, no randomness. Returns full time series plus
    mission-relevant summaries (final/peak/onset of the syndrome index and the
    influence ratio at the horizon).
    """
    if days <= 0:
        raise ValueError("days must be positive")
    if dt <= 0:
        raise ValueError("dt must be positive")
    if not 0.0 <= onset_threshold <= 1.0:
        raise ValueError("onset_threshold must be in [0, 1]")
    if len(initial_state) != 3 or any(v < 0 or v > 1 for v in initial_state):
        raise ValueError("initial_state must be three fractions in [0, 1]")
    params = params or DynamicsParams()

    t = 0.0
    state: tuple[float, float, float] = (
        float(initial_state[0]),
        float(initial_state[1]),
        float(initial_state[2]),
    )
    day_list: list[float] = []
    fear_list: list[float] = []
    grat_list: list[float] = []
    ident_list: list[float] = []
    synd_list: list[float] = []
    onset: float | None = None
    peak = -1.0
    peak_day = 0.0

    steps = round(days / dt)
    for _ in range(steps):
        day_list.append(t)
        fear_list.append(state[0])
        grat_list.append(state[1])
        ident_list.append(state[2])
        synd = syndrome_index(state)
        synd_list.append(synd)
        if synd >= onset_threshold and onset is None:
            onset = t
        if synd > peak:
            peak = synd
            peak_day = t
        threat = threat_schedule(params, t)
        kindness = _kindness_input(events, t)
        state = rk4_step(state, params, threat, kindness, dt)
        t += dt
    # final point
    day_list.append(t)
    fear_list.append(state[0])
    grat_list.append(state[1])
    ident_list.append(state[2])
    synd_list.append(syndrome_index(state))
    final = syndrome_index(state)

    denom = state[0] + state[1] + state[2] + 1e-9
    influence = state[2] / denom
    return HostageDynamicsResult(
        days=day_list,
        fear=fear_list,
        gratitude=grat_list,
        identification=ident_list,
        syndrome=synd_list,
        params=params,
        final_syndrome=final,
        peak_syndrome=peak if peak >= 0 else final,
        peak_day=peak_day,
        onset_day=onset,
        influence_ratio=influence,
    )

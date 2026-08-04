"""Real-data tests for the hostage-psychology influence model (ELEKTRA pillar 3).

Zero mocks: asserts the ODE system's boundedness, determinism, no-kindness and
sustained-kindness regimes, and RK4 accuracy against an analytic decay
solution.
"""

from __future__ import annotations

import math

import pytest

from the_world_is_not_enough import hostage_psychology as H


class TestDynamicsParams:
    def test_negative_rate_rejected(self) -> None:
        with pytest.raises(ValueError):
            H.DynamicsParams(fear_decay=-0.1)

    def test_default_returns_params(self) -> None:
        assert H.DynamicsParams().threat_initial == 0.75


class TestKindnessEvent:
    def test_negative_day_rejected(self) -> None:
        with pytest.raises(ValueError):
            H.KindnessEvent(day=-1.0, magnitude=0.5)

    def test_magnitude_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            H.KindnessEvent(day=1.0, magnitude=1.5)
        with pytest.raises(ValueError):
            H.KindnessEvent(day=1.0, magnitude=-0.2)


class TestThreatSchedule:
    def test_decays_and_bounded(self) -> None:
        params = H.DynamicsParams()
        t0 = H.threat_schedule(params, 0.0)
        t10 = H.threat_schedule(params, 10.0)
        assert t0 > t10
        assert params.threat_floor <= t10 <= params.threat_floor + params.threat_initial

    def test_negative_time_clamped(self) -> None:
        assert H.threat_schedule(H.DynamicsParams(), -5.0) == H.threat_schedule(
            H.DynamicsParams(), 0.0
        )


class TestDerivativesAndRK4:
    def test_derivatives_deterministic(self) -> None:
        params = H.DynamicsParams()
        a = H.derivatives((0.5, 0.2, 0.1), params, 0.4, 0.3)
        b = H.derivatives((0.5, 0.2, 0.1), params, 0.4, 0.3)
        assert a == b

    def test_rk4_step_advances(self) -> None:
        params = H.DynamicsParams()
        state = (0.7, 0.0, 0.02)
        nxt = H.rk4_step(state, params, 0.4, 0.3, 0.25)
        assert all(isinstance(v, float) for v in nxt)
        assert len(nxt) == 3

    def test_analytic_decay_match(self) -> None:
        # With threat/kindness/gratitude-identification couplings off
        # (b=c=e=0), the fear state reduces to dF/dt = -aF -> F(t)=F0 exp(-a t).
        params = H.DynamicsParams(
            threat_sensitivity=0.0,
            kindness_gain=0.0,
            gratitude_decay=0.05,
            ident_gain=0.0,
            fear_suppress=0.0,
        )
        result = H.integrate_dynamics(
            days=10.0,
            dt=0.01,
            params=params,
            events=(),
            initial_state=(1.0, 0.0, 0.0),
        )
        expected = math.exp(-params.fear_decay * 10.0)
        assert result.fear[-1] == pytest.approx(expected, abs=1e-3)


class TestSyndromeIndex:
    def test_clamps_low(self) -> None:
        assert H.syndrome_index((1.0, 0.0, 0.0)) == 0.0  # F high, no G/I

    def test_clamps_high(self) -> None:
        assert H.syndrome_index((0.0, 1.0, 1.0)) == 1.0

    def test_in_range(self) -> None:
        for state in ((0.3, 0.3, 0.3), (0.8, 0.1, 0.5), (0.9, 0.9, 0.0)):
            assert 0.0 <= H.syndrome_index(state) <= 1.0


class TestIntegrate:
    def test_invalid_args(self) -> None:
        with pytest.raises(ValueError):
            H.integrate_dynamics(days=0.0)
        with pytest.raises(ValueError):
            H.integrate_dynamics(dt=-0.1)
        with pytest.raises(ValueError):
            H.integrate_dynamics(onset_threshold=1.5)
        with pytest.raises(ValueError):
            H.integrate_dynamics(initial_state=(1.5, 0.0, 0.02))  # value out of [0,1]

    def test_default_reaches_onset(self) -> None:
        result = H.integrate_dynamics()
        assert result.onset_day is not None
        assert 0.0 < result.onset_day <= 30.0
        assert result.peak_syndrome > 0.5
        assert 0.0 <= result.final_syndrome <= 1.0

    def test_influence_ratio_in_range(self) -> None:
        result = H.integrate_dynamics()
        assert 0.0 <= result.influence_ratio <= 1.0

    def test_all_states_bounded(self) -> None:
        result = H.integrate_dynamics()
        for series in (
            result.fear,
            result.gratitude,
            result.identification,
            result.syndrome,
        ):
            assert all(-1e-6 <= v <= 1.0 + 1e-6 for v in series)

    def test_deterministic(self) -> None:
        a = H.integrate_dynamics()
        b = H.integrate_dynamics()
        assert a.as_dict() == b.as_dict()
        assert a.fear == b.fear

    def test_no_kindness_stays_low(self) -> None:
        params = H.DynamicsParams(kindness_gain=0.0)
        result = H.integrate_dynamics(params=params, events=())
        assert result.final_syndrome < 0.3
        assert result.onset_day is None

    def test_sustained_kindness_low_threat_high(self) -> None:
        params = H.DynamicsParams(
            threat_initial=0.1,
            threat_floor=0.02,
            threat_sensitivity=0.05,
            kindness_gain=0.9,
            ident_gain=0.7,
            fear_suppress=0.02,
        )
        events = tuple(H.KindnessEvent(day=float(d), magnitude=0.9) for d in range(20))
        result = H.integrate_dynamics(days=20.0, dt=0.5, params=params, events=events)
        assert result.final_syndrome > 0.7

    def test_as_dict_summary(self) -> None:
        result = H.integrate_dynamics()
        d = result.as_dict()
        assert d["final_syndrome"] == result.final_syndrome
        assert d["onset_day"] == result.onset_day
        assert "fear_final" in d


class TestMathExp:
    def test_values(self) -> None:
        assert H.math_exp(0.0) == pytest.approx(1.0)
        assert H.math_exp(1.0) == pytest.approx(math.e)

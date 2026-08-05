"""Real-data tests for the hostage-negotiation bargaining model (ELEKTRA).

Zero mocks: asserts the Rubinstein equilibrium formula, the syndrome-driven
patience mapping, and the concession settlement against hand-computed values.
"""

from __future__ import annotations

import pytest

from the_world_is_not_enough import negotiation_tactics as N


class TestNegotiationParams:
    def test_defaults_valid(self) -> None:
        params = N.NegotiationParams()
        assert params.pie == 1.0
        assert params.negotiator_discount == 0.90

    def test_nonpositive_pie(self) -> None:
        with pytest.raises(ValueError):
            N.NegotiationParams(pie=0.0)

    def test_numeric_type(self) -> None:
        with pytest.raises(TypeError):
            N.NegotiationParams(negotiator_discount="x")  # type: ignore[arg-type]

    def test_captor_base_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            N.NegotiationParams(captor_discount_base=1.0)

    def test_gain_too_large(self) -> None:
        with pytest.raises(ValueError):
            N.NegotiationParams(captor_discount_gain=1.0, captor_discount_base=0.5)

    def test_negotiator_discount_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            N.NegotiationParams(negotiator_discount=1.0)
        with pytest.raises(ValueError):
            N.NegotiationParams(negotiator_discount=0.0)

    def test_nonpositive_deadline(self) -> None:
        with pytest.raises(ValueError):
            N.NegotiationParams(deadline_days=0.0)

    def test_initial_positions_order(self) -> None:
        with pytest.raises(ValueError):
            N.NegotiationParams(initial_demand=0.5, initial_offer=0.6)

    def test_nonpositive_concession_rate(self) -> None:
        with pytest.raises(ValueError):
            N.NegotiationParams(concession_rate=0.0)


class TestEquilibriumShares:
    def test_known_value(self) -> None:
        captor, negotiator = N.equilibrium_shares(0.6, 0.9)
        assert captor == pytest.approx(0.2174, abs=1e-3)
        assert negotiator == pytest.approx(0.7826, abs=1e-3)
        assert captor + negotiator == pytest.approx(1.0)

    def test_patient_captor_wins_more(self) -> None:
        slow = N.equilibrium_shares(0.6, 0.9)[0]
        patient = N.equilibrium_shares(0.8, 0.9)[0]
        assert patient > slow

    def test_invalid_discounts(self) -> None:
        with pytest.raises(ValueError):
            N.equilibrium_shares(1.0, 0.9)
        with pytest.raises(ValueError):
            N.equilibrium_shares(0.6, 0.0)
        with pytest.raises(TypeError):
            N.equilibrium_shares("x", 0.9)  # type: ignore[arg-type]


class TestRubinsteinSplit:
    def test_proposer_first(self) -> None:
        captor_split = N.rubinstein_split(0.6, 0.9, proposer="captor")
        negotiator_split = N.rubinstein_split(0.6, 0.9, proposer="negotiator")
        captor, _ = N.equilibrium_shares(0.6, 0.9)
        assert captor_split == pytest.approx(captor)
        assert negotiator_split == pytest.approx(1.0 - captor)

    def test_invalid_proposer(self) -> None:
        with pytest.raises(ValueError):
            N.rubinstein_split(0.6, 0.9, proposer="arbiter")


class TestCaptorDiscountFromSyndrome:
    def test_monotonic(self) -> None:
        assert N.captor_discount_from_syndrome(0.0) < N.captor_discount_from_syndrome(
            0.5
        )
        assert N.captor_discount_from_syndrome(0.5) < N.captor_discount_from_syndrome(
            1.0
        )

    def test_canonical_value(self) -> None:
        assert N.captor_discount_from_syndrome(0.532) == pytest.approx(0.7894, abs=1e-3)

    def test_clamps_at_0_99(self) -> None:
        assert N.captor_discount_from_syndrome(
            1.0, base=0.5, gain=0.5
        ) == pytest.approx(0.99)
        assert N.captor_discount_from_syndrome(1.0, base=0.5, gain=0.5) <= 0.99

    def test_invalid_syndrome(self) -> None:
        with pytest.raises(ValueError):
            N.captor_discount_from_syndrome(1.5)
        with pytest.raises(ValueError):
            N.captor_discount_from_syndrome(-0.1)
        with pytest.raises(TypeError):
            N.captor_discount_from_syndrome("x")  # type: ignore[arg-type]

    def test_invalid_base_gain(self) -> None:
        with pytest.raises(ValueError):
            N.captor_discount_from_syndrome(0.5, base=-0.1)
        with pytest.raises(ValueError):
            N.captor_discount_from_syndrome(0.5, base=0.7, gain=0.5)


class TestSettlementAnalysis:
    def test_both_args_rejected(self) -> None:
        with pytest.raises(ValueError):
            N.settlement_analysis(syndrome=0.5, captor_discount=0.7)

    def test_canonical_settles(self) -> None:
        outcome = N.settlement_analysis(syndrome=0.532)
        assert outcome["reached"] is True
        assert outcome["reason"] == "settled"
        assert outcome["settlement_day"] == pytest.approx(5.625, abs=1e-6)
        assert outcome["settlement_split"] == pytest.approx(0.5)
        assert outcome["captor_discount"] == pytest.approx(0.7894, abs=1e-3)

    def test_shared_monotonic_in_syndrome(self) -> None:
        low = N.settlement_analysis(syndrome=0.0)
        high = N.settlement_analysis(syndrome=0.6)
        assert float(high["captor_share"]) > float(low["captor_share"])

    def test_stalemate_for_patient_captor(self) -> None:
        outcome = N.settlement_analysis(captor_discount=0.97)
        assert outcome["reached"] is False
        assert outcome["reason"] == "stalemate"
        assert outcome["settlement_day"] is None

    def test_deadline_lapse(self) -> None:
        params = N.NegotiationParams(deadline_days=1.0)
        outcome = N.settlement_analysis(params, syndrome=0.532)
        assert outcome["reached"] is False
        assert outcome["reason"] == "deadline"

    def test_explicit_captor_discount(self) -> None:
        outcome = N.settlement_analysis(captor_discount=0.7)
        assert outcome["captor_discount"] == pytest.approx(0.7)

    def test_deterministic(self) -> None:
        a = N.settlement_analysis(syndrome=0.532)
        b = N.settlement_analysis(syndrome=0.532)
        assert a == b

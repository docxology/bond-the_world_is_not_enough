"""Hostage-negotiation tactics: bargaining under Stockholm-syndrome influence.

ELEKTRA's fifth pillar deepens the hostage-psychology model into the
negotiation layer. Two real, deterministic pieces of bargaining mathematics:

* **Rubinstein alternating-offer bargaining** [@rubinstein] — with discount
  factors :math:`\\delta_c` (captor) and :math:`\\delta_n` (negotiator) and
  the captor proposing first, the subgame-perfect equilibrium gives the
  captor the share
  :math:`x_c = \\frac{1-\\delta_n}{1-\\delta_c\\,\\delta_n}` of the pie.

* **Syndrome-driven patience** — the Stockholm-syndrome state feeds back into
  the captor's discount factor: as identification with the captor grows
  (:class:`~the_world_is_not_enough.hostage_psychology`), the captor values
  the relationship more, becomes more patient (higher discount factor), and
  extracts a larger equilibrium share. Patience beyond a threshold makes the
  equilibrium shares disjoint — the negotiation *stalemates*.

A deterministic concession model then resolves the outcome in time: the
captor's demand concedes toward its equilibrium share and the negotiator's
offer rises toward its own; settlement occurs at the first crossing (or the
deadline, or never). All mathematics is closed-form and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "NegotiationParams",
    "captor_discount_from_syndrome",
    "equilibrium_shares",
    "rubinstein_split",
    "settlement_analysis",
]

_PROPOSERS = ("captor", "negotiator")


@dataclass(frozen=True)
class NegotiationParams:
    """Deterministic bargaining configuration.

    ``pie`` is the total stake (fraction-of-pie shares are reported against
    it), ``captor_discount_base``/``captor_discount_gain`` map the syndrome
    index onto the captor's patience, ``negotiator_discount`` is the
    negotiator's patience, ``deadline_days`` bounds the concession phase, and
    ``initial_demand``/``initial_offer``/``concession_rate`` drive the
    per-day concession dynamics.
    """

    pie: float = 1.0
    captor_discount_base: float = 0.55
    captor_discount_gain: float = 0.45
    negotiator_discount: float = 0.90
    deadline_days: float = 10.0
    initial_demand: float = 0.95
    initial_offer: float = 0.05
    concession_rate: float = 0.08

    def __post_init__(self) -> None:
        if self.pie <= 0:
            raise ValueError("NegotiationParams.pie must be positive")
        for name, value in self.__dict__.items():
            if name == "pie":
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"NegotiationParams.{name} must be numeric")
        if not 0.0 <= self.captor_discount_base < 1.0:
            raise ValueError("NegotiationParams.captor_discount_base must be in [0, 1)")
        if self.captor_discount_gain < 0:
            raise ValueError(
                "NegotiationParams.captor_discount_gain must be non-negative"
            )
        if self.captor_discount_base + self.captor_discount_gain > 1.0:
            raise ValueError("captor_discount_base + gain must not exceed 1")
        if not 0.0 < self.negotiator_discount < 1.0:
            raise ValueError("NegotiationParams.negotiator_discount must be in (0, 1)")
        if self.deadline_days <= 0:
            raise ValueError("NegotiationParams.deadline_days must be positive")
        if not 0.0 < self.initial_offer < self.initial_demand < 1.0:
            raise ValueError(
                "NegotiationParams needs 0 < initial_offer < initial_demand < 1"
            )
        if self.concession_rate <= 0:
            raise ValueError("NegotiationParams.concession_rate must be positive")


def _validate_discount(discount: float, label: str) -> None:
    if isinstance(discount, bool) or not isinstance(discount, (int, float)):
        raise TypeError(f"{label} must be numeric")
    if not 0.0 < discount < 1.0:
        raise ValueError(f"{label} must be in (0, 1), got {discount}")


def equilibrium_shares(
    captor_discount: float,
    negotiator_discount: float,
) -> tuple[float, float]:
    """Subgame-perfect equilibrium shares ``(captor, negotiator)`` of the pie.

    With the captor proposing first in Rubinstein's alternating-offer game,
    the captor's share is ``(1 - delta_n) / (1 - delta_c * delta_n)`` and the
    negotiator keeps the remainder. A more patient party captures more.
    """
    _validate_discount(captor_discount, "captor_discount")
    _validate_discount(negotiator_discount, "negotiator_discount")
    captor_share = (1.0 - negotiator_discount) / (
        1.0 - captor_discount * negotiator_discount
    )
    return (float(captor_share), float(1.0 - captor_share))


def rubinstein_split(
    captor_discount: float,
    negotiator_discount: float,
    *,
    proposer: str = "captor",
) -> float:
    """Equilibrium share of the pie for the party that proposes first."""
    if proposer not in _PROPOSERS:
        raise ValueError(f"proposer must be one of {_PROPOSERS}, got {proposer!r}")
    captor_share, negotiator_share = equilibrium_shares(
        captor_discount, negotiator_discount
    )
    return captor_share if proposer == "captor" else negotiator_share


def captor_discount_from_syndrome(
    syndrome: float,
    base: float = 0.55,
    gain: float = 0.45,
) -> float:
    """Map the Stockholm-syndrome index onto the captor's discount factor.

    As identification with the captor rises, the captor's attachment to the
    relationship grows, so it becomes more patient (higher discount factor).
    ``base + gain * syndrome`` is clamped to ``0.99``.
    """
    if isinstance(syndrome, bool) or not isinstance(syndrome, (int, float)):
        raise TypeError("syndrome must be numeric")
    if not 0.0 <= syndrome <= 1.0:
        raise ValueError(f"syndrome must be in [0, 1], got {syndrome}")
    if base < 0 or gain < 0:
        raise ValueError("base and gain must be non-negative")
    if base + gain > 1.0:
        raise ValueError("base + gain must not exceed 1")
    return float(min(0.99, base + gain * syndrome))


def settlement_analysis(
    params: NegotiationParams | None = None,
    *,
    syndrome: float | None = None,
    captor_discount: float | None = None,
) -> dict[str, object]:
    """Resolve the concession game to settlement (or stalemate).

    The captor's demand falls from ``initial_demand`` toward its equilibrium
    share at ``concession_rate`` per day; the negotiator's offer rises from
    ``initial_offer`` toward its own equilibrium share. Settlement is the
    first day the offer meets or exceeds the demand. When the equilibrium
    shares are disjoint (a patient, syndrome-driven captor demands more than
    the negotiator can concede), no agreement exists; when the crossing falls
    after ``deadline_days``, the deadline lapses.

    Args:
        params: Bargaining configuration (defaults to the canonical scenario).
        syndrome: Optional syndrome index driving ``captor_discount``.
        captor_discount: Optional explicit captor discount (overrides
            ``syndrome``).

    Returns a deterministic outcome dict (fraction-of-pie shares and days).
    """
    params = params or NegotiationParams()
    if syndrome is not None and captor_discount is not None:
        raise ValueError("pass either syndrome or captor_discount, not both")
    if captor_discount is None:
        syndrome_index = syndrome if syndrome is not None else 0.5
        captor_discount = captor_discount_from_syndrome(
            syndrome_index,
            base=params.captor_discount_base,
            gain=params.captor_discount_gain,
        )
    captor_discount = float(captor_discount)
    _validate_discount(captor_discount, "captor_discount")

    captor_share, negotiator_share = equilibrium_shares(
        captor_discount, params.negotiator_discount
    )
    if captor_share > negotiator_share:
        return {
            "reached": False,
            "reason": "stalemate",
            "settlement_day": None,
            "settlement_split": None,
            "captor_share": captor_share,
            "negotiator_share": negotiator_share,
            "captor_discount": captor_discount,
        }

    rate = params.concession_rate
    demand_floor_time = (params.initial_demand - captor_share) / rate
    offer_ceiling_time = (negotiator_share - params.initial_offer) / rate
    raw_cross_time = (params.initial_demand - params.initial_offer) / (2.0 * rate)

    if raw_cross_time <= min(demand_floor_time, offer_ceiling_time):
        settlement_day = raw_cross_time
        settlement_split = 0.5 * (params.initial_demand + params.initial_offer)
    elif offer_ceiling_time < demand_floor_time:
        settlement_day = (params.initial_demand - negotiator_share) / rate
        settlement_split = negotiator_share
    else:
        settlement_day = (captor_share - params.initial_offer) / rate
        settlement_split = captor_share

    if settlement_day > params.deadline_days:
        return {
            "reached": False,
            "reason": "deadline",
            "settlement_day": None,
            "settlement_split": None,
            "captor_share": captor_share,
            "negotiator_share": negotiator_share,
            "captor_discount": captor_discount,
        }
    return {
        "reached": True,
        "reason": "settled",
        "settlement_day": float(settlement_day),
        "settlement_split": float(settlement_split),
        "captor_share": captor_share,
        "negotiator_share": negotiator_share,
        "captor_discount": captor_discount,
    }

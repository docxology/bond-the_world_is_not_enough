"""The claim ledger must bind to live model output, not drift beside it.

``data/claim_ledger.yaml`` registers the package's headline numeric claims.
Before these tests existed the ledger was never read by anything: its values
were hand-written duplicates of measured results that could go stale silently
while the file's own header asserted the claims were auditable.

These tests make the ledger enforced. Every entry must name a token that
``manuscript_variables.generate_variables()`` actually produces, must record
that token's live value exactly, and must point at a source file that exists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from the_world_is_not_enough import manuscript_variables as MV

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "claim_ledger.yaml"

REQUIRED_FIELDS = ("id", "claim", "value", "unit", "source", "evidence")


def _claims() -> list[dict[str, Any]]:
    with LEDGER.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict), "claim ledger must be a mapping"
    claims = data["claims"]
    assert isinstance(claims, list), "claim ledger 'claims' must be a list"
    return claims


CLAIMS = _claims()
CLAIM_IDS = [str(claim["id"]) for claim in CLAIMS]


def stale_claims(claims: list[dict[str, Any]], variables: dict[str, str]) -> list[str]:
    """Ids of ledger entries whose recorded value is not the live token value.

    This is *the* gate: both the per-claim test and the falsifiability control
    below route through it, so a control that passes while the comparison is
    broken is impossible. An entry citing a token nobody generates is stale by
    definition.
    """
    stale: list[str] = []
    for claim in claims:
        token = str(claim["evidence"])
        if token not in variables or str(claim["value"]) != variables[token]:
            stale.append(str(claim["id"]))
    return stale


class TestLedgerStructure:
    def test_ledger_is_not_empty(self) -> None:
        """A vacuous ledger would make every parametrized test below pass."""
        assert len(CLAIMS) >= 9

    def test_ids_are_unique(self) -> None:
        assert len(CLAIM_IDS) == len(set(CLAIM_IDS))

    @pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
    def test_required_fields_present(self, claim: dict[str, Any]) -> None:
        for field in REQUIRED_FIELDS:
            assert field in claim, f"{claim.get('id')} missing {field!r}"
            assert str(claim[field]).strip(), f"{claim.get('id')} has blank {field!r}"


class TestLedgerBindsToMeasuredOutput:
    """Each recorded value must equal the live token it cites."""

    @pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
    def test_evidence_token_is_generated(self, claim: dict[str, Any]) -> None:
        variables = MV.generate_variables()
        token = str(claim["evidence"])
        assert token in variables, (
            f"{claim['id']} cites {token}, which manuscript_variables does not generate"
        )

    @pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
    def test_recorded_value_matches_the_live_token(self, claim: dict[str, Any]) -> None:
        variables = MV.generate_variables()
        token = str(claim["evidence"])
        assert not stale_claims([claim], variables), (
            f"{claim['id']} records {claim['value']!r} but {token} is "
            f"{variables.get(token)!r} — regenerate the ledger from the models"
        )

    @pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
    def test_source_file_exists(self, claim: dict[str, Any]) -> None:
        source = str(claim["source"]).split("::", 1)[0]
        assert (ROOT / source).is_file(), f"{claim['id']} cites missing {source}"


class TestLedgerCanFail:
    """Mutation control on the gate itself, not on string inequality.

    The earlier version of this class asserted
    ``str(claim['value']) + '9' != variables[token]`` — true for *any* string,
    for any code, forever. It demonstrated nothing. These tests instead run
    :func:`stale_claims` (the same function the suite above depends on) over a
    corrupted copy of the real ledger and require it to flag the corruption,
    with the uncorrupted ledger as the positive control. Break the comparison
    inside ``stale_claims`` and this class goes red.
    """

    @staticmethod
    def _corrupt(index: int, **overrides: Any) -> list[dict[str, Any]]:
        claims = [dict(claim) for claim in CLAIMS]
        claims[index].update(overrides)
        return claims

    def test_positive_control_the_real_ledger_is_clean(self) -> None:
        assert stale_claims(CLAIMS, MV.generate_variables()) == []

    @pytest.mark.parametrize("index", range(len(CLAIMS)))
    def test_a_drifted_value_is_flagged(self, index: int) -> None:
        """Perturbing any single recorded value must be caught, not just the first."""
        variables = MV.generate_variables()
        original = str(CLAIMS[index]["value"])
        drifted = f"{float(original) * 1.01:.3f}" if _is_number(original) else "XXX"
        assert drifted != original
        claims = self._corrupt(index, value=drifted)
        assert stale_claims(claims, variables) == [CLAIM_IDS[index]]

    def test_a_claim_citing_an_unknown_token_is_flagged(self) -> None:
        claims = self._corrupt(0, evidence="RESULT_NO_SUCH_TOKEN")
        assert stale_claims(claims, MV.generate_variables()) == [CLAIM_IDS[0]]

    def test_the_gate_reports_every_drifted_entry_not_just_the_first(self) -> None:
        variables = MV.generate_variables()
        claims = [dict(claim) | {"value": "definitely-wrong"} for claim in CLAIMS]
        assert stale_claims(claims, variables) == CLAIM_IDS


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True

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
        assert str(claim["value"]) == variables[token], (
            f"{claim['id']} records {claim['value']!r} but {token} is "
            f"{variables[token]!r} — regenerate the ledger from the models"
        )

    @pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
    def test_source_file_exists(self, claim: dict[str, Any]) -> None:
        source = str(claim["source"]).split("::", 1)[0]
        assert (ROOT / source).is_file(), f"{claim['id']} cites missing {source}"


class TestLedgerCanFail:
    """The binding above is a real gate, not a formality."""

    def test_a_corrupted_value_would_not_match(self) -> None:
        variables = MV.generate_variables()
        claim = CLAIMS[0]
        token = str(claim["evidence"])
        corrupted = str(claim["value"]) + "9"
        assert corrupted != variables[token]

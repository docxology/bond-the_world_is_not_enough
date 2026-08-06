"""Guard-rail tests (V4): the "zero mocks" and "no template lineage" hard rules.

Both were documented as hard rules in AGENTS.md and verified manually, but
nothing in tests/ enforced either, so a violation would slip through silently.
These tests walk the package tree and fail on the mock-framework patterns or
the lineage string — with a positive control proving the matcher can fire — so
the rules are gates, not aspirations.

Every detectable literal is assembled at runtime from character codes, so this
file's own source cannot contain a substring its matchers would flag (a guard
that trips on its own detection strings would be unmaintainable and would mask
the very violations it exists to catch).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _word(*codes: int) -> str:
    """Assemble a word from char codes so the literal never appears in source."""
    return "".join(chr(c) for c in codes)


MOCK = _word(109, 111, 99, 107)  # "mock"
MOCKER = _word(109, 111, 99, 107, 101, 114)  # "mocker"
MONKEY = _word(109, 111, 110, 107, 101, 121)  # "monkey"
PATCH = _word(112, 97, 116, 99, 104)  # "patch"
LINEAGE = (
    _word(116, 101, 109, 112, 108, 97, 116, 101)
    + "_"
    + _word(99, 111, 100, 101)
    + "_"
    + _word(112, 114, 111, 106, 101, 99, 116)
)

#: Framework-name regexes (assembled) — mocker/monkey/Mock only appear joined.
MOCK_PATTERNS = (
    r"\bunittest\." + MOCK + r"\b",
    r"\bMagic" + MOCK + r"\b",
    r"\bMock" + r"\(",
    r"\b" + MOCKER + r"[\s(.,\[]",
    r"\b" + MONKEY + PATCH + r"\b",
    r"\bMock" + PATCH + r"\b",
)


def _walk(*relative: str) -> list[Path]:
    out = [path for rel in relative for path in sorted((ROOT / rel).rglob("*.py"))]
    return out


class TestZeroMocks:
    def test_live_positive_control_a_planted_mock_is_detected(self) -> None:
        """The matcher fires on a planted string — the gate is not vacuous."""
        planted = (
            "from "
            + _word(117, 110, 105, 116, 116, 101, 115, 116)
            + " import "
            + MOCK
            + "\n"
            + "x = "
            + MOCKER
            + "."
            + PATCH
            + "('y')\n"
        )
        assert any(re.search(pattern, planted) for pattern in MOCK_PATTERNS), (
            "positive control: a planted mock was not detected"
        )

    def test_no_mock_framework_in_source_or_scripts(self) -> None:
        offenders: list[str] = []
        for path in _walk("src", "scripts"):
            text = path.read_text(encoding="utf-8")
            for pattern in MOCK_PATTERNS:
                if re.search(pattern, text):
                    offenders.append(f"{path}: {pattern}")
        assert not offenders, f"mock patterns found in package code: {offenders}"

    def test_no_mock_framework_in_tests(self) -> None:
        offenders: list[str] = []
        for path in _walk("tests"):
            text = path.read_text(encoding="utf-8")
            for pattern in MOCK_PATTERNS:
                if re.search(pattern, text):
                    offenders.append(f"{path}: {pattern}")
        assert not offenders, f"mock patterns found in tests: {offenders}"


class TestNoLineage:
    def test_live_positive_control_the_lineage_string_is_detected(self) -> None:
        """The matcher still matches the plain string."""
        plain = LINEAGE
        assert re.search(LINEAGE, "delete " + plain + " now")

    def test_no_plain_lineage_string_in_source(self) -> None:
        offenders = [
            str(path)
            for path in _walk("src", "scripts")
            if re.search(LINEAGE, path.read_text(encoding="utf-8"))
        ]
        assert not offenders, f"template lineage string in package code: {offenders}"

    def test_no_plain_lineage_string_in_tests(self) -> None:
        offenders = [
            str(path)
            for path in _walk("tests")
            if re.search(LINEAGE, path.read_text(encoding="utf-8"))
        ]
        assert not offenders, f"template lineage string in tests: {offenders}"

"""Tests for manuscript variable hydration (tokens never hand-authored)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from the_world_is_not_enough import manuscript_variables as MV

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "manuscript" / "config.yaml"
MANUSCRIPT = ROOT / "manuscript"


class TestLoadConfig:
    def test_loads_default(self) -> None:
        config = MV.load_manuscript_config()
        assert isinstance(config, dict)
        assert "paper" in config

    def test_missing_path_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            MV.load_manuscript_config(CONFIG.parent / "nope.yaml")

    def test_non_mapping_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises(TypeError):
            MV.load_manuscript_config(bad)


class TestGenerateVariables:
    def test_identity_tokens(self) -> None:
        variables = MV.generate_variables()
        assert variables["MISSION_CODENAME"] == "ELEKTRA"
        assert variables["MISSION_FILM"] == "The World Is Not Enough (1999)"
        assert variables["PACKAGE_VERSION"] == MV.PACKAGE_VERSION

    def test_result_tokens_present(self) -> None:
        variables = MV.generate_variables()
        for key in (
            "RESULT_MAX_FLOW",
            "RESULT_MIN_CUT_CAPACITY",
            "RESULT_CHOKE_POINT_COUNT",
            "RESULT_TOP_CHOKE_POINT",
            "RESULT_TAMPER_DETECTION_RATE",
            "RESULT_EXPOSURE_REDUCTION",
            "RESULT_SYNDROME_FINAL",
            "RESULT_SYNDROME_ONSET_DAY",
        ):
            assert key in variables

    def test_measured_values(self) -> None:
        variables = MV.generate_variables()
        assert variables["RESULT_MAX_FLOW"] == "420.000"
        assert variables["RESULT_MIN_CUT_CAPACITY"] == "420.000"
        assert variables["RESULT_CHOKE_POINT_COUNT"] == "1"
        assert variables["RESULT_TOP_CHOKE_POINT"] == "J4->J5"
        assert variables["RESULT_EXPOSURE_REDUCTION"] == "24.861"
        assert variables["RESULT_SYNDROME_ONSET_DAY"] == "11.250"

    def test_all_values_strings(self) -> None:
        variables = MV.generate_variables()
        assert all(isinstance(v, str) for v in variables.values())

    def test_timestamp_deterministic_with_now(self) -> None:
        now = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)
        a = MV.generate_variables(now=now)
        b = MV.generate_variables(now=now)
        assert a["GENERATION_TIMESTAMP"] == b["GENERATION_TIMESTAMP"]

    def test_strict_require_outputs(self) -> None:
        # require_outputs=False still resolves everything (results are measured inline)
        assert MV.generate_variables() == MV.generate_variables(require_outputs=False)


class TestResolveTree:
    def test_writes_resolved_sections(self, tmp_path: Path) -> None:
        variables = {"MISSION_CODENAME": "ELEKTRA", "A_TOKEN": "42"}
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "03_results.md").write_text(
            "codename {{MISSION_CODENAME}} = {{A_TOKEN}}\n", encoding="utf-8"
        )
        out_dir, names = MV.resolve_manuscript_tree(
            variables, manuscript_dir=src_dir, output_dir=tmp_path / "out"
        )
        assert names == ["03_results.md"]
        resolved = (out_dir / "03_results.md").read_text(encoding="utf-8")
        assert "codename ELEKTRA = 42" in resolved

    def test_strict_fails_on_unresolved(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "04_missing.md").write_text("{{UNKNOWN_TOKEN}}\n", encoding="utf-8")
        with pytest.raises(ValueError):
            MV.resolve_manuscript_tree(
                {"A": "1"}, manuscript_dir=src_dir, output_dir=tmp_path / "out"
            )

    def test_non_strict_writes_raw(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "05_raw.md").write_text("{{UNKNOWN_TOKEN}}\n", encoding="utf-8")
        out_dir, _ = MV.resolve_manuscript_tree(
            {"A": "1"},
            manuscript_dir=src_dir,
            output_dir=tmp_path / "out",
            strict=False,
        )
        assert "{{UNKNOWN_TOKEN}}" in (out_dir / "05_raw.md").read_text(
            encoding="utf-8"
        )


class TestLiveCrossReference:
    def test_every_prose_token_is_generated(self) -> None:
        """Every {{TOKEN}} in a numbered manuscript section must be generated."""
        variables = MV.generate_variables()
        token_re = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
        for section in sorted(MANUSCRIPT.glob("[0-9][0-9]_*.md")):
            text = section.read_text(encoding="utf-8")
            found = set(token_re.findall(text))
            missing = found - set(variables)
            assert not missing, (
                f"unresolved tokens in {section.name}: {sorted(missing)}"
            )

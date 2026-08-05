"""Tests for manuscript variable hydration (tokens never hand-authored)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

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
        assert variables["RESULT_BLACKOUT_LOST_MW"] == "220.000"
        assert variables["CONFIG_GRID_BUSES"] == "8"
        assert variables["RESULT_NEG_SETTLEMENT_DAY"] == "5.625"
        assert variables["RESULT_TRACK_MEASUREMENT_RMSE"] == "2.912"

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

    def test_derived_dataset_tokens_match_the_models(self) -> None:
        """CONFIG_* tokens describing the datasets are derived, never typed."""
        from the_world_is_not_enough import pipeline_security, power_grid

        variables = MV.generate_variables()
        network = pipeline_security.default_pipeline()
        grid = power_grid.default_power_grid()
        assert variables["CONFIG_PIPELINE_NODES"] == str(network.node_count())
        assert variables["CONFIG_PIPELINE_SEGMENTS"] == str(network.edge_count)
        assert variables["CONFIG_GRID_BUSES"] == str(grid.n_buses)
        assert variables["CONFIG_GRID_LINES"] == str(len(grid.lines))
        assert variables["CONFIG_CHOKE_UTILIZATION"] == "90"
        assert variables["CONFIG_GRID_STRONG_TIE_MW"] == "400"
        assert variables["CONFIG_GRID_WEAK_TIE"] == "4->5"
        assert variables["CONFIG_GRID_WEAK_TIE_MW"] == "150"
        assert variables["CONFIG_GRID_LOAD_MW"] == "500"

    def test_negotiation_baseline_is_the_unboosted_equilibrium(self) -> None:
        """RESULT_NEG_BASELINE_SHARE must equal the no-syndrome equilibrium."""
        from the_world_is_not_enough import negotiation_tactics

        variables = MV.generate_variables()
        params = negotiation_tactics.NegotiationParams(
            deadline_days=10.0, negotiator_discount=0.90, concession_rate=0.08
        )
        expected, _ = negotiation_tactics.equilibrium_shares(
            params.captor_discount_base, params.negotiator_discount
        )
        assert variables["RESULT_NEG_BASELINE_SHARE"] == f"{expected:.3f}"
        assert float(variables["RESULT_NEG_CAPTOR_SHARE"]) > expected

    def test_experiment_section_must_be_a_mapping(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(
            "paper: {title: T}\nexperiment: not-a-mapping\n", encoding="utf-8"
        )
        with pytest.raises(TypeError, match="experiment"):
            MV.generate_variables(config_path=bad)

    def test_config_token_helper_rejects_a_non_mapping_experiment(self) -> None:
        with pytest.raises(TypeError, match="experiment"):
            MV._config_tokens({"experiment": "not-a-mapping"})

    def test_paper_section_must_be_a_mapping(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("paper: not-a-mapping\nexperiment: {seed: 1999}\n", "utf-8")
        with pytest.raises(TypeError, match="paper"):
            MV.generate_variables(config_path=bad)


class TestMeasurabilityGate:
    """`_assert_measurable` must be able to fail — it is not green by construction."""

    def test_accepts_the_real_measured_tokens(self) -> None:
        MV._assert_measurable(MV.generate_variables())

    def test_rejects_an_empty_token_map(self) -> None:
        with pytest.raises(ValueError, match="no result tokens"):
            MV._assert_measurable({})

    def test_rejects_a_blank_value(self) -> None:
        with pytest.raises(ValueError, match="empty value"):
            MV._assert_measurable({"RESULT_MAX_FLOW": "   "})

    @pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
    def test_rejects_non_finite_values(self, bad: str) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            MV._assert_measurable({"RESULT_MAX_FLOW": bad})

    def test_allows_sentinels_and_categorical_values(self) -> None:
        MV._assert_measurable(
            {
                "RESULT_SYNDROME_ONSET_DAY": "not reached",
                "RESULT_NEG_SETTLEMENT_SPLIT": "none",
                "RESULT_TOP_CHOKE_POINT": "J4->J5",
            }
        )

    def test_rejects_a_real_token_map_with_one_value_corrupted(self) -> None:
        """The gate rejects exactly the map the manuscript would otherwise render.

        The failure path cannot currently be reached through
        ``generate_variables`` with any config: every domain model validates
        its own inputs and refuses a degenerate experiment block before a
        non-finite value can be produced (see
        ``test_degenerate_config_is_refused_by_the_models``). The gate is
        defence in depth against a future model change, so it is exercised
        here against the real token map with a single value corrupted.
        """
        variables = MV.generate_variables()
        assert "RESULT_BLACKOUT_FRACTION" in variables
        corrupted = dict(variables)
        corrupted["RESULT_BLACKOUT_FRACTION"] = "nan"
        with pytest.raises(ValueError, match="RESULT_BLACKOUT_FRACTION"):
            MV._assert_measurable(corrupted)

    def test_degenerate_config_is_refused_by_the_models(self, tmp_path: Path) -> None:
        """Degenerate experiment blocks fail loudly upstream of the gate."""
        config = MV.load_manuscript_config()
        config["experiment"]["hostage"]["days"] = 0.0
        bad = tmp_path / "degenerate.yaml"
        bad.write_text(yaml.safe_dump(config), encoding="utf-8")
        with pytest.raises(ValueError, match="days must be positive"):
            MV.generate_variables(config_path=bad)


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

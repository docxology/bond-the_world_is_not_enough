"""Tests for manuscript variable hydration (tokens never hand-authored)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

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

    def test_edition_stamp_is_the_committed_config_date(self) -> None:
        """The one time-valued token reads `paper.date`, not the clock."""
        config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        declared = str(config["paper"]["date"])
        variables = MV.generate_variables()
        assert variables["MANUSCRIPT_EDITION_STAMP"].startswith(declared)
        assert variables["MANUSCRIPT_EDITION_STAMP"] == f"{declared}T00:00:00+00:00"

    def test_edition_stamp_follows_an_edited_config_date(self, tmp_path: Path) -> None:
        """Editing `paper.date` moves the stamp — it is consumed, not decorative."""
        config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        config["paper"]["date"] = "1999-11-19"  # the film's US release date
        edited = tmp_path / "config.yaml"
        edited.write_text(yaml.safe_dump(config), encoding="utf-8")
        variables = MV.generate_variables(config_path=edited)
        assert variables["MANUSCRIPT_EDITION_STAMP"] == "1999-11-19T00:00:00+00:00"

    def test_no_wall_clock_reaches_the_token_set(self) -> None:
        """No token carries today's date unless the config declares it.

        A regression that restored `datetime.now()` would put the current UTC
        date into the token set; this pins that it is absent.
        """
        config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        today = datetime.now(timezone.utc).date().isoformat()
        if str(config["paper"]["date"]) == today:
            pytest.skip("config date is today; the negative control cannot bind")
        variables = MV.generate_variables()
        offenders = {k: v for k, v in variables.items() if today in v}
        assert not offenders, f"wall-clock date leaked into tokens: {offenders}"

    def test_missing_config_date_fails_closed(self, tmp_path: Path) -> None:
        """A deleted `paper.date` raises rather than defaulting to now()."""
        config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        del config["paper"]["date"]
        edited = tmp_path / "config.yaml"
        edited.write_text(yaml.safe_dump(config), encoding="utf-8")
        with pytest.raises(KeyError, match="paper.date"):
            MV.generate_variables(config_path=edited)

    def test_unparsable_config_date_raises(self, tmp_path: Path) -> None:
        config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        config["paper"]["date"] = "the nineteenth of November"
        edited = tmp_path / "config.yaml"
        edited.write_text(yaml.safe_dump(config), encoding="utf-8")
        with pytest.raises(ValueError):
            MV.generate_variables(config_path=edited)

    def test_edition_stamp_accepts_an_unquoted_yaml_date(self) -> None:
        """PyYAML parses an unquoted `2026-08-04` to `datetime.date`."""
        assert (
            MV.edition_stamp({"date": date(2026, 8, 4)}) == "2026-08-04T00:00:00+00:00"
        )

    def test_edition_stamp_accepts_a_yaml_datetime(self) -> None:
        assert (
            MV.edition_stamp({"date": datetime(2026, 8, 4, 9, 30, tzinfo=timezone.utc)})
            == "2026-08-04T00:00:00+00:00"
        )

    def test_edition_stamp_rejects_blank(self) -> None:
        with pytest.raises(KeyError):
            MV.edition_stamp({"date": "   "})

    def test_strict_require_outputs(self) -> None:
        """require_outputs=False still resolves everything — results are measured inline.

        This used to pin `now=` because the two hydrations each re-run all six
        models and could straddle a second boundary, making the timestamp token
        differ. That flake was the visible symptom of the real defect: the
        token set was clock-dependent. It is now config-derived, so the two
        calls compare directly with nothing injected.
        """
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


class TestUnitConsistencyGate:
    """`_assert_units_consistent` guards the manuscript's physical units.

    It exists because the tamper simulation once reported a cumulative volume
    of 9660 under a ``kbbl/day`` label — 23x the corridor's 420 kbbl/day max
    flow and 1.51x its total installed capacity.
    """

    def test_accepts_the_real_measured_tokens(self) -> None:
        variables = MV.generate_variables()
        results = {k: v for k, v in variables.items() if k.startswith("RESULT_")}
        MV._assert_units_consistent(results)

    def test_every_result_token_declares_a_unit(self) -> None:
        variables = MV.generate_variables()
        results = {k for k in variables if k.startswith("RESULT_")}
        assert results == set(MV.RESULT_TOKEN_UNITS)

    def test_rejects_an_undeclared_result_token(self) -> None:
        with pytest.raises(ValueError, match="without a declared unit"):
            MV._assert_units_consistent({"RESULT_BRAND_NEW_NUMBER": "1.0"})

    def test_a_categorical_value_under_a_rate_unit_is_skipped_not_crashed(
        self,
    ) -> None:
        """A sentinel in a rate slot has no magnitude to bound — it must not crash."""
        MV._assert_units_consistent({"RESULT_MAX_FLOW": "not reached"})

    def test_the_declared_and_derived_name_sets_match_the_builders(self) -> None:
        """The frozen name sets are enforced here, not by an unreachable in-code guard."""
        config = MV.load_manuscript_config()
        assert set(MV._declared_config_tokens(config)) == MV.DECLARED_CONFIG_TOKENS
        assert set(MV._derived_dataset_tokens(config)) == MV.DERIVED_DATASET_TOKENS

    def test_rejects_a_volume_mislabelled_as_a_rate(self) -> None:
        """The exact historical defect: the tamper volume labelled kbbl/day."""
        from the_world_is_not_enough import pipeline_security

        variables = MV.generate_variables()
        volume = variables["RESULT_TAMPER_THROUGHPUT_LOST"]
        installed = sum(e.capacity for e in pipeline_security.default_pipeline().edges)
        assert float(volume) > installed, "the historical value must exceed the ceiling"
        with pytest.raises(ValueError, match="it is not a rate"):
            MV._assert_units_consistent({"RESULT_MAX_FLOW": volume})

    def test_the_tamper_loss_is_a_volume_not_a_rate(self) -> None:
        assert MV.RESULT_TOKEN_UNITS["RESULT_TAMPER_THROUGHPUT_LOST"] == "kbbl"

    def test_rate_tokens_respect_their_physical_ceiling(self) -> None:
        from the_world_is_not_enough import pipeline_security, power_grid

        variables = MV.generate_variables()
        ceilings = {
            "kbbl/day": sum(
                e.capacity for e in pipeline_security.default_pipeline().edges
            ),
            "MW": power_grid.total_load(power_grid.default_power_grid()),
        }
        checked = 0
        for token, unit in MV.RESULT_TOKEN_UNITS.items():
            if unit not in ceilings:
                continue
            checked += 1
            assert float(variables[token]) <= ceilings[unit], token
        assert checked >= 3, "the ceiling check must actually cover rate tokens"


class TestTamperVolumeAccounting:
    """The reported tamper loss must be a volume with a real downtime factor."""

    def test_volume_scales_with_the_downtime_window(self) -> None:
        from the_world_is_not_enough import pipeline_security as P

        net = P.default_pipeline()
        one = P.simulate_tamper(net, 40, 1999, nominal_downtime_days=1.0)
        two = P.simulate_tamper(net, 40, 1999, nominal_downtime_days=2.0)
        assert float(two["throughput_lost_kbbl"]) == pytest.approx(
            2.0 * float(one["throughput_lost_kbbl"])
        )
        assert float(one["throughput_lost_kbbl"]) > 0.0

    def test_per_event_charge_never_exceeds_a_daily_capacity(self) -> None:
        """Each event's charge / downtime is a legal per-day rate for its segment."""
        from the_world_is_not_enough import pipeline_security as P

        net = P.default_pipeline()
        capacity = {e.id: e.capacity for e in net.edges}
        result = P.simulate_tamper(net, 60, 1999, nominal_downtime_days=3.0)
        downtime = float(result["nominal_downtime_days"])
        events = result["events"]
        assert isinstance(events, list) and events
        for event in events:
            rate = float(event["throughput_lost_kbbl"]) / downtime
            assert rate <= capacity[str(event["edge"])] + 1e-9

    def test_zero_or_negative_downtime_is_refused(self) -> None:
        from the_world_is_not_enough import pipeline_security as P

        with pytest.raises(ValueError, match="nominal_downtime_days"):
            P.simulate_tamper(P.default_pipeline(), 5, 1, nominal_downtime_days=0.0)


class TestLeverageIsRelativeNotAbsolute:
    """RESULT_NEG_CAPTOR_LEVERAGE_PCT is a relative increase, in percent."""

    def test_leverage_reconstructs_the_captor_share(self) -> None:
        variables = MV.generate_variables()
        baseline = float(variables["RESULT_NEG_BASELINE_SHARE"])
        share = float(variables["RESULT_NEG_CAPTOR_SHARE"])
        pct = float(variables["RESULT_NEG_CAPTOR_LEVERAGE_PCT"])
        assert baseline * (1.0 + pct / 100.0) == pytest.approx(share, abs=5e-4)

    def test_leverage_is_not_an_absolute_share_difference(self) -> None:
        """Reading it as an added share would imply a share above 0.9."""
        variables = MV.generate_variables()
        baseline = float(variables["RESULT_NEG_BASELINE_SHARE"])
        share = float(variables["RESULT_NEG_CAPTOR_SHARE"])
        pct = float(variables["RESULT_NEG_CAPTOR_LEVERAGE_PCT"])
        assert abs((share - baseline) - pct / 100.0) > 0.3

    def test_it_is_declared_a_percent_like_its_siblings(self) -> None:
        for token in (
            "RESULT_NEG_CAPTOR_LEVERAGE_PCT",
            "RESULT_EXPOSURE_REDUCTION",
            "RESULT_TRACK_GAIN",
        ):
            assert MV.RESULT_TOKEN_UNITS[token] == "percent"


HOSTAGE_RATES = (
    "fear_decay",
    "threat_sensitivity",
    "kindness_gain",
    "gratitude_decay",
    "ident_gain",
    "fear_suppress",
    "threat_initial",
    "threat_decay",
    "threat_floor",
)


class TestHostageParametersAreReallyConfigured:
    """§7 claims the hostage rate constants are exposed in config.yaml for audit.

    Naming a knob in a YAML file proves nothing; these tests perturb each one
    and assert the reported syndrome index moves, so the claim is about
    consumption, not about the file's contents.
    """

    @staticmethod
    def _syndrome_with(tmp_path: Path, mutate: Any) -> str:
        config = MV.load_manuscript_config()
        mutate(config)
        path = tmp_path / "perturbed.yaml"
        path.write_text(yaml.safe_dump(config), encoding="utf-8")
        return MV.generate_variables(config_path=path)["RESULT_SYNDROME_FINAL"]

    def test_the_shipped_config_declares_every_rate(self) -> None:
        rates = MV.load_manuscript_config()["experiment"]["hostage"]["dynamics"]
        assert set(rates) == set(HOSTAGE_RATES)

    def test_config_rates_drive_the_model(self) -> None:
        """The DynamicsParams the manuscript uses come from the file, not defaults."""
        from the_world_is_not_enough import hostage_psychology

        hostage = MV.load_manuscript_config()["experiment"]["hostage"]
        built = MV.hostage_params(hostage)
        assert built == hostage_psychology.DynamicsParams(
            **hostage["dynamics"],
        )

    @pytest.mark.parametrize("rate", HOSTAGE_RATES)
    def test_perturbing_each_rate_moves_the_result(
        self, tmp_path: Path, rate: str
    ) -> None:
        baseline = MV.generate_variables()["RESULT_SYNDROME_FINAL"]

        def mutate(config: dict[str, Any]) -> None:
            dynamics = config["experiment"]["hostage"]["dynamics"]
            dynamics[rate] = float(dynamics[rate]) * 2.0 + 0.05

        assert self._syndrome_with(tmp_path, mutate) != baseline

    def test_perturbing_the_kindness_schedule_moves_the_result(
        self, tmp_path: Path
    ) -> None:
        baseline = MV.generate_variables()["RESULT_SYNDROME_FINAL"]

        def mutate(config: dict[str, Any]) -> None:
            config["experiment"]["hostage"]["kindness_events"] = [
                {"day": 1.0, "magnitude": 0.2}
            ]

        assert self._syndrome_with(tmp_path, mutate) != baseline

    def test_perturbing_the_initial_state_moves_the_result(
        self, tmp_path: Path
    ) -> None:
        baseline = MV.generate_variables()["RESULT_SYNDROME_FINAL"]

        def mutate(config: dict[str, Any]) -> None:
            config["experiment"]["hostage"]["initial_state"] = [0.1, 0.4, 0.5]

        assert self._syndrome_with(tmp_path, mutate) != baseline

    @pytest.mark.parametrize(
        ("knob", "value"),
        [
            ("captor_discount_base", 0.30),
            ("captor_discount_gain", 0.20),
            ("initial_demand", 0.80),
            ("initial_offer", 0.02),
        ],
    )
    def test_perturbing_each_bargaining_knob_moves_a_result(
        self, tmp_path: Path, knob: str, value: float
    ) -> None:
        before = MV.generate_variables()
        config = MV.load_manuscript_config()
        config["experiment"]["negotiation"][knob] = value
        path = tmp_path / "neg.yaml"
        path.write_text(yaml.safe_dump(config), encoding="utf-8")
        after = MV.generate_variables(config_path=path)
        moved = {
            token
            for token in (
                "RESULT_NEG_CAPTOR_SHARE",
                "RESULT_NEG_BASELINE_SHARE",
                "RESULT_NEG_SETTLEMENT_DAY",
                "RESULT_NEG_SETTLEMENT_SPLIT",
            )
            if before[token] != after[token]
        }
        assert moved, f"{knob} is declared in config.yaml but consumed by nothing"

    def test_a_deleted_rate_fails_closed(self) -> None:
        """C2: a missing rate raises rather than silently defaulting.

        The hostage accessors used to fall back to module defaults (identical
        to the config values), so deleting `fear_decay` changed no output and
        no test went red. They now fail closed: `manuscript/config.yaml` is the
        single authority and a deleted knob cannot pass unnoticed.
        """
        missing = dict(MV.load_manuscript_config()["experiment"]["hostage"])
        del missing["dynamics"]["fear_decay"]
        with pytest.raises(KeyError, match="fear_decay"):
            MV.hostage_params(missing)

    def test_a_deleted_kindness_schedule_fails_closed(self) -> None:
        missing = dict(MV.load_manuscript_config()["experiment"]["hostage"])
        del missing["kindness_events"]
        with pytest.raises(KeyError, match="kindness_events"):
            MV.kindness_events(missing)

    def test_a_deleted_initial_state_fails_closed(self) -> None:
        missing = dict(MV.load_manuscript_config()["experiment"]["hostage"])
        del missing["initial_state"]
        with pytest.raises(KeyError, match="initial_state"):
            MV.hostage_initial_state(missing)

    def test_the_experiment_block_is_required(self) -> None:
        """The shared scenario builder refuses a config with no `experiment:`."""
        config = MV.load_manuscript_config()
        del config["experiment"]
        with pytest.raises(KeyError, match="experiment"):
            MV.build_mission_scenario(config)

    @pytest.mark.parametrize("rate", HOSTAGE_RATES)
    def test_deleting_any_single_rate_fails_closed(self, rate: str) -> None:
        """Every one of the nine declared rates is individually required."""
        config = MV.load_manuscript_config()
        del config["experiment"]["hostage"]["dynamics"][rate]
        with pytest.raises(KeyError, match=rate):
            MV.generate_variables(
                config_path=ROOT / "_staging_deleted_rate.yaml"
            ) if False else MV.build_mission_scenario(config)

    def test_malformed_blocks_are_refused(self) -> None:
        with pytest.raises(TypeError, match="dynamics"):
            MV.hostage_params({"dynamics": "not-a-mapping"})
        with pytest.raises(TypeError, match="kindness_events"):
            MV.kindness_events({"kindness_events": "not-a-list"})
        with pytest.raises(TypeError, match="initial_state"):
            MV.hostage_initial_state({"initial_state": [0.1, 0.2]})


class TestSharedScenarioBuilder:
    """Hostile coverage of the `build_mission_scenario` validation arms.

    The scenario builder is the single source of truth for the mission and the
    manuscript, so *every* malformed-input guard must be proven reachable with
    a real (bad) config — not by an unreachable defensive branch.
    """

    @staticmethod
    def _with(config: dict[str, Any], path: list[str], value: Any) -> dict[str, Any]:
        target: Any = config
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        return config

    def test_deleted_experiment_block_raises(self) -> None:
        with pytest.raises(KeyError, match="experiment"):
            MV.build_mission_scenario({"paper": {"title": "x"}})

    @pytest.mark.parametrize(
        ("path", "msg"),
        [
            (["experiment"], "mapping"),
            (["experiment", "pipeline"], "pipeline"),
            (["experiment", "submarine"], "submarine"),
            (["experiment", "hostage"], "hostage"),
            (["experiment", "power_grid"], "power_grid"),
            (["experiment", "negotiation"], "negotiation"),
            (["experiment", "fusion"], "fusion"),
        ],
    )
    def test_non_mapping_section_raises(self, tmp_path: Path, path, msg) -> None:
        config = MV.load_manuscript_config()
        self._with(config, path, "not-a-mapping")
        with pytest.raises(TypeError, match=msg):
            MV.build_mission_scenario(config)

    def test_bad_submarine_start_pair_raises(self) -> None:
        config = MV.load_manuscript_config()
        config["experiment"]["submarine"]["start"] = [1]
        with pytest.raises(TypeError, match="x, y"):
            MV.build_mission_scenario(config)


class TestSetupTableSourceColumn:
    """§5's Source column must match the code's declared/derived partition.

    The section previously asserted that all of its rows were injected "from
    config.yaml" while nine of them were read off fixed module datasets.
    """

    SETUP = MANUSCRIPT / "05_experimental_setup.md"
    ROW = re.compile(r"^\|\s*[^|]+\|\s*`([A-Z0-9_]+)`\s*\|\s*([^|]+?)\s*\|")

    def _rows(self) -> dict[str, str]:
        rows: dict[str, str] = {}
        for line in self.SETUP.read_text(encoding="utf-8").splitlines():
            match = self.ROW.match(line)
            if match:
                rows[match.group(1)] = match.group(2)
        return rows

    def test_the_table_is_parsed_at_all(self) -> None:
        assert len(self._rows()) >= 30

    def test_every_config_token_appears_in_the_table(self) -> None:
        variables = MV.generate_variables()
        expected = {k for k in variables if k.startswith("CONFIG_")}
        assert expected - set(self._rows()) == set()

    def test_declared_rows_are_labelled_config_yaml(self) -> None:
        rows = self._rows()
        mislabelled = {
            token
            for token in MV.DECLARED_CONFIG_TOKENS
            if rows.get(token) != "config.yaml"
        }
        assert not mislabelled

    def test_derived_rows_are_labelled_derived(self) -> None:
        rows = self._rows()
        mislabelled = {
            token for token in MV.DERIVED_DATASET_TOKENS if rows.get(token) != "derived"
        }
        assert not mislabelled

    def test_the_two_sets_are_disjoint_and_complete(self) -> None:
        variables = MV.generate_variables()
        config_tokens = {k for k in variables if k.startswith("CONFIG_")}
        assert MV.DECLARED_CONFIG_TOKENS & MV.DERIVED_DATASET_TOKENS == frozenset()
        assert MV.DECLARED_CONFIG_TOKENS | MV.DERIVED_DATASET_TOKENS == config_tokens

    def test_derived_tokens_ignore_the_config_file(self, tmp_path: Path) -> None:
        """A derived row cannot be moved by editing config.yaml — that is the claim."""
        config = MV.load_manuscript_config()
        config["experiment"]["pipeline"]["nodes"] = 999
        config["experiment"]["power_grid"]["buses"] = 999
        config["experiment"]["choke_utilization"] = 0.1
        path = tmp_path / "derived.yaml"
        path.write_text(yaml.safe_dump(config), encoding="utf-8")
        after = MV.generate_variables(config_path=path)
        before = MV.generate_variables()
        for token in MV.DERIVED_DATASET_TOKENS:
            assert after[token] == before[token]


class TestExampleConfigIsInSync:
    def test_example_matches_the_live_config_below_its_header(self) -> None:
        live = (MANUSCRIPT / "config.yaml").read_text(encoding="utf-8")
        example = (MANUSCRIPT / "config.yaml.example").read_text(encoding="utf-8")
        body = live.split("\npaper:", 1)[1]
        assert example.split("\npaper:", 1)[1] == body


class TestArchitectureDocumentsThePublicSurface:
    """docs/architecture.md must name every exported symbol it claims to describe.

    The doc listed the validated dataclass for five of six pillars and named
    none of `hostage_psychology`'s — 293 lines of public parameter and result
    surface documented nowhere.
    """

    DOC = ROOT / "docs" / "architecture.md"
    MODULES = (
        "pipeline_security",
        "sub_defense",
        "hostage_psychology",
        "power_grid",
        "negotiation_tactics",
        "sensor_fusion",
        "figures",
        "manuscript_variables",
        "mission",
    )

    def test_every_exported_name_is_documented(self) -> None:
        import importlib

        text = self.DOC.read_text(encoding="utf-8")
        missing: list[str] = []
        checked = 0
        for name in self.MODULES:
            module = importlib.import_module(f"the_world_is_not_enough.{name}")
            for symbol in module.__all__:
                checked += 1
                if symbol not in text:
                    missing.append(f"{name}.{symbol}")
        assert checked > 50, "the doc gate must actually inspect a public surface"
        assert not missing, f"undocumented public symbols: {sorted(missing)}"


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


class TestRegenerationDeterminism:
    """The byte-identity claim in `manuscript/06_reproducibility.md`, enforced.

    This runs the *real* generator twice and diffs the *persisted bytes*. It
    injects nothing — no fixed clock, no frozen `now`. That distinction is the
    whole point: the package previously shipped
    `test_timestamp_deterministic_with_now`, which passed a pinned `now=` into
    both calls and therefore could not observe that the default path read
    `datetime.now()` and wrote a different byte stream on every run. A test
    that supplies the determinism it is meant to be checking proves nothing.

    Reintroducing a wall clock anywhere in the token set turns this red.
    """

    SCRIPT = ROOT / "scripts" / "z_generate_manuscript_variables.py"

    @staticmethod
    def _artifacts(root: Path) -> dict[str, bytes]:
        """Every persisted artifact under `root`, keyed by relative path."""
        return {
            str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*"))
            if p.is_file()
        }

    def _generate(self, out: Path) -> dict[str, bytes]:
        proc = subprocess.run(
            [sys.executable, str(self.SCRIPT), "--output-dir", str(out)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        artifacts = self._artifacts(out)
        assert artifacts, "generator wrote nothing — the comparison would be vacuous"
        return artifacts

    def test_two_runs_a_second_apart_are_byte_identical(self, tmp_path: Path) -> None:
        first = self._generate(tmp_path / "run_a")
        time.sleep(1.1)  # straddle a second boundary: a clock would differ here
        second = self._generate(tmp_path / "run_b")

        assert sorted(first) == sorted(second)
        differing = sorted(k for k in first if first[k] != second[k])
        assert not differing, f"regeneration is not byte-identical: {differing}"

    def test_the_comparison_covers_the_json_and_the_resolved_prose(
        self, tmp_path: Path
    ) -> None:
        """Positive control: the byte set actually includes the claimed files.

        A determinism assertion over an empty or JSON-only file set would be
        green by construction, so pin that both halves of the claim's scope —
        the variables JSON and the resolved manuscript sections — are compared.
        """
        artifacts = self._generate(tmp_path / "run")
        assert "data/manuscript_variables.json" in artifacts
        sections = [
            k
            for k in artifacts
            if k.startswith("manuscript/")
            and re.fullmatch(r"\d\d_.+\.md", Path(k).name)
        ]
        assert len(sections) >= 3, f"resolved prose missing from comparison: {sections}"

    def test_a_clock_valued_token_would_be_caught(self, tmp_path: Path) -> None:
        """Failability control: the byte comparison detects a per-run value.

        This does not touch the shipped generator. It writes the same artifact
        shape twice with one clock-derived field, a second apart, and shows the
        comparison used above goes red — so a green result from the real
        generator is evidence, not an artifact of a comparison that cannot
        fail.
        """

        def write(out: Path) -> dict[str, bytes]:
            target = out / "data" / "manuscript_variables.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            target.write_text(
                json.dumps({"MANUSCRIPT_EDITION_STAMP": stamp}), encoding="utf-8"
            )
            return self._artifacts(out)

        first = write(tmp_path / "clock_a")
        time.sleep(1.1)
        second = write(tmp_path / "clock_b")
        assert sorted(first) == sorted(second)
        assert any(first[k] != second[k] for k in first), (
            "the byte comparison cannot detect a wall clock — it is vacuous"
        )

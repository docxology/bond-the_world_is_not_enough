"""Tests for the ELEKTRA MissionProvider adapter (bond_api protocol binding).

Zero mocks: exercises the real provider against the FROZEN bond_api protocol —
conformance, full five-stage flow, determinism, gadget registration, and
slug-based discovery.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from bond_api.discovery import load_provider
from bond_api.protocol import (
    MissionOutcome,
    Provenance,
    ReconRequest,
    run_mission,
)
from bond_api.protocol import (
    MissionProvider as Protocol,
)
from bond_api.serialization import from_json, to_json

from the_world_is_not_enough import mission

SRC = Path(__file__).resolve().parents[1] / "src"


def make_provider() -> mission.MissionProvider:
    return mission.MissionProvider()


class TestProviderConformance:
    def test_film_identity(self) -> None:
        assert mission.FILM == "the_world_is_not_enough"
        assert make_provider().film == mission.FILM

    def test_is_runtime_checkable(self) -> None:
        assert isinstance(make_provider(), Protocol)

    def test_brief_fields(self) -> None:
        brief = make_provider().brief()
        assert brief.film == mission.FILM
        assert brief.codename == "ELEKTRA"
        assert len(brief.objectives) == 4
        assert len(brief.assets) == 6
        kinds = {asset.kind for asset in brief.assets}
        assert kinds == {
            "pipeline",
            "submarine",
            "hostage",
            "power",
            "negotiation",
            "fusion",
        }
        constraint_kinds = {c.kind for c in brief.constraints}
        assert "determinism" in constraint_kinds

    def test_recon_report(self) -> None:
        report = make_provider().recon(ReconRequest(goal="survey everything"))
        assert report.findings
        labels = {f.label for f in report.findings}
        assert {
            "goal",
            "pipeline",
            "submarine",
            "hostage",
            "power",
            "negotiation",
            "fusion",
        } <= labels

    def test_plan_steps(self) -> None:
        provider = make_provider()
        plan = provider.plan(provider.brief())
        assert len(plan.steps) == 8
        assert plan.steps[0].action == "analyze_choke_points"
        assert plan.steps[-1].action == "track_submarine"


class TestExecute:
    def test_outcome_shape(self) -> None:
        provider = make_provider()
        plan = provider.plan(provider.brief())
        outcome = provider.execute(plan)
        assert isinstance(outcome, MissionOutcome)
        assert outcome.success is True
        assert outcome.results["steps_completed"] == 8
        assert "max_flow_kbpd" in outcome.results
        assert "syndrome_final" in outcome.results
        assert "blackout_fraction" in outcome.results
        assert "neg_captor_share" in outcome.results
        assert "track_filter_rmse" in outcome.results
        assert isinstance(outcome.provenance, Provenance)

    def test_provenance_fields(self) -> None:
        provider = make_provider()
        outcome = provider.execute(provider.plan(provider.brief()))
        assert outcome.provenance.package_version == mission.PACKAGE_VERSION
        assert outcome.provenance.seed == 1999
        assert outcome.provenance.input_hash
        assert outcome.provenance.wall_time_s == 0.0

    def test_deterministic(self) -> None:
        provider = make_provider()
        plan = provider.plan(provider.brief())
        a = provider.execute(plan)
        b = provider.execute(plan)
        assert a.results == b.results
        assert a.provenance.input_hash == b.provenance.input_hash

    def test_input_hash_stable_across_identical_plans(self) -> None:
        provider = make_provider()
        plan = provider.plan(provider.brief())
        h1 = mission.mission_input_hash(plan)
        h2 = mission.mission_input_hash(plan)
        assert h1 == h2
        assert len(h1) == 64  # sha256 hex

    def test_the_scenario_consumes_every_config_leaf(self) -> None:
        """V1/C1: every `experiment:` leaf is consumed by the shared scenario.

        The adapter used to restate every knob as a module constant, held in
        check by a hand-written mirror test that could not see an *added*,
        unmapped config key. That restatement is gone: `mission.py` now builds
        its inputs from `manuscript_variables.build_mission_scenario()`, the
        *single* reader of the `experiment:` block. This test supplies the
        completeness half the mirror could not: it walks the config's leaf
        paths (list indices normalised away) and asserts the scenario builder
        read every one, so an un-consumed key turns the suite red.
        """
        from the_world_is_not_enough import manuscript_variables as MV

        config = MV.load_manuscript_config()
        MV.build_mission_scenario(config)
        consumed = MV._CONSUMED_CONFIG_KEYS

        def leaves(node: Any, prefix: str = "experiment") -> set[str]:
            """Every leaf dotted-path in ``experiment:``, list indices removed.

            A config ``sensors`` list contributes one canonical path per field
            (``experiment.submarine.sensors.x``), matching how the builder
            records its reads, so list *shape* never trips the guard.
            """
            out: set[str] = set()
            for key, value in node.items():
                here = f"{prefix}.{key}"
                if isinstance(value, dict):
                    out |= leaves(value, here)
                elif isinstance(value, list):
                    for element in value:
                        if isinstance(element, dict):
                            out |= leaves(element, here)
                        else:
                            out.add(here)
                else:
                    out.add(here)
            return out

        declared = leaves(config["experiment"])
        canonical: set[str] = set()
        for path in declared:
            parts = [p for p in path.split(".") if not p.isdigit()]
            canonical.add(".".join(parts))

        missing = canonical - consumed
        assert not missing, (
            f"config leaves not consumed by build_mission_scenario: {sorted(missing)}"
        )

    def test_the_scenario_rejects_a_degenerate_leaf(self) -> None:
        """A leaf that turns into an invalid model input fails closed."""
        from the_world_is_not_enough import manuscript_variables as MV

        config = MV.load_manuscript_config()
        del config["experiment"]["submarine"]["sensors"]
        with pytest.raises(KeyError, match="sensors"):
            MV.build_mission_scenario(config)

    def test_mission_and_manuscript_measure_the_same_run(self) -> None:
        """The adapter mirrors `manuscript/config.yaml` — assert it, don't assume it.

        `docs/architecture.md` claims mission and manuscript agree because
        `mission.py`'s module constants mirror the `experiment:` block. Nothing
        enforced that: the manuscript now reads its hostage rate constants and
        bargaining schedule from the config file, so a config edit that the
        adapter does not follow must fail here rather than silently publish two
        different runs.
        """
        from the_world_is_not_enough import manuscript_variables as MV

        provider = make_provider()
        results = provider.execute(provider.plan(provider.brief())).results
        variables = MV.generate_variables()
        pairs = {
            "max_flow_kbpd": "RESULT_MAX_FLOW",
            "syndrome_final": "RESULT_SYNDROME_FINAL",
            "syndrome_peak": "RESULT_SYNDROME_PEAK",
            "syndrome_onset_day": "RESULT_SYNDROME_ONSET_DAY",
            "influence_ratio": "RESULT_INFLUENCE_RATIO",
            "neg_captor_share": "RESULT_NEG_CAPTOR_SHARE",
            "blackout_lost_load_mw": "RESULT_BLACKOUT_LOST_MW",
            "tamper_throughput_lost_kbbl": "RESULT_TAMPER_THROUGHPUT_LOST",
        }
        for key, token in pairs.items():
            assert key in results, key
            assert f"{float(results[key]):.3f}" == variables[token], (
                f"mission {key}={results[key]} disagrees with manuscript "
                f"{token}={variables[token]}"
            )

    def test_measured_values(self) -> None:
        provider = make_provider()
        r = provider.execute(provider.plan(provider.brief())).results
        assert r["max_flow_kbpd"] == pytest.approx(420.0)
        assert r["min_cut_capacity_kbpd"] == pytest.approx(420.0)
        assert r["choke_point_count"] == 1
        assert r["top_choke_point"] == "J4->J5"
        assert 0.0 < r["exposure_reduction"] < 1.0
        assert r["syndrome_final"] > 0.5
        assert r["syndrome_onset_day"] is not None
        assert r["blackout_lost_load_mw"] == pytest.approx(220.0)
        assert r["blackout_fraction"] == pytest.approx(0.44)
        assert r["blackout_lines_tripped"] == 2
        assert r["neg_reached"] is True
        assert r["neg_settlement_day"] == pytest.approx(5.625, abs=1e-6)
        assert 0.0 < r["neg_captor_share"] < 1.0
        assert r["track_filter_rmse"] < r["track_measurement_rmse"]
        assert r["track_converged"] is True


class TestDebrief:
    def test_lessons_derived(self) -> None:
        provider = make_provider()
        outcome = provider.execute(provider.plan(provider.brief()))
        debrief = provider.debrief(outcome)
        assert len(debrief.lessons) >= 3
        assert debrief.outcome is outcome
        assert any("choke" in lesson.lower() for lesson in debrief.lessons)


class TestRunMission:
    def test_full_flow(self) -> None:
        provider = make_provider()
        debrief = run_mission(provider, ReconRequest(goal="execute ELEKTRA"))
        assert isinstance(debrief.outcome, MissionOutcome)
        assert debrief.outcome.success is True


class TestGadgets:
    def test_registry_contents(self) -> None:
        assert mission.FILM in mission.GADGETS
        gadgets = mission.GADGETS.gadgets_for(mission.FILM)
        assert set(gadgets) >= {
            "pipeline_analysis",
            "tamper_simulation",
            "evasion_analysis",
            "hostage_dynamics",
            "power_cascade",
            "negotiation_settlement",
            "submarine_tracking",
            "mission_input_hash",
        }

    def test_gadget_lookup_returns_callables(self) -> None:
        analyzer = mission.GADGETS.lookup(mission.FILM, "pipeline_analysis")
        from the_world_is_not_enough import pipeline_security

        report = analyzer(pipeline_security.default_pipeline())
        assert report["max_flow_kbpd"] == pytest.approx(420.0)

    def test_lookup_missing_raises(self) -> None:
        with pytest.raises(KeyError):
            mission.GADGETS.lookup("no_such_film", "x")
        with pytest.raises(KeyError):
            mission.GADGETS.lookup(mission.FILM, "no_such_gadget")


class TestSerialization:
    def test_brief_round_trip(self) -> None:
        provider = make_provider()
        brief = provider.brief()
        restored = from_json(to_json(brief))
        assert restored == brief

    def test_outcome_round_trip(self) -> None:
        provider = make_provider()
        outcome = provider.execute(provider.plan(provider.brief()))
        restored = from_json(to_json(outcome))
        assert restored == outcome
        assert restored.results == outcome.results


class TestDiscovery:
    def test_load_provider_by_slug(self) -> None:
        provider = load_provider("the_world_is_not_enough", search_paths=[str(SRC)])
        assert provider.film == mission.FILM
        assert isinstance(provider, Protocol)
        assert provider.brief().codename == "ELEKTRA"

    def test_load_provider_bad_slug(self) -> None:
        from bond_api.discovery import DiscoveryError

        with pytest.raises(DiscoveryError):
            load_provider("does_not_exist_xyz", search_paths=[str(SRC)])

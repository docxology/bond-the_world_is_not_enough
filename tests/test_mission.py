"""Tests for the ELEKTRA MissionProvider adapter (bond_api protocol binding).

Zero mocks: exercises the real provider against the FROZEN bond_api protocol —
conformance, full five-stage flow, determinism, gadget registration, and
slug-based discovery.
"""

from __future__ import annotations

from pathlib import Path

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

    def test_every_mirrored_constant_equals_its_config_key(self) -> None:
        """Bind each `mission.py` constant to the config key it mirrors.

        `docs/architecture.md` says the adapter constants mirror the
        `experiment:` block "so the mission and the manuscript measure the same
        run". Nothing enforced that: editing `config.yaml` to
        `tamper_events: 41` left the whole suite green while the adapter still
        ran 40. Every mirrored value is now pinned here, so the convention is a
        checked guarantee rather than an unenforced comment.
        """
        from the_world_is_not_enough import manuscript_variables as MV

        exp = MV.load_manuscript_config()["experiment"]
        assert mission.SEED == exp["seed"]
        assert mission._TAMPER_EVENTS == exp["pipeline"]["tamper_events"]
        assert mission._DETECT_PROB == exp["pipeline"]["detection_probability"]

        sub = exp["submarine"]
        assert mission._SUB_GRID == sub["grid_size"]
        assert mission._SUB_STEP_M == sub["step_m"]
        assert list(mission._SUB_START) == sub["start"]
        assert list(mission._SUB_GOAL) == sub["goal"]
        assert len(mission._SUB_SENSORS) == len(sub["sensors"])
        for sensor, declared in zip(mission._SUB_SENSORS, sub["sensors"], strict=True):
            assert (sensor.x, sensor.y) == (declared["x"], declared["y"])
            assert sensor.source_level == declared["source_level"]
            assert sensor.noise_level == declared["noise_level"]
            assert sensor.absorption_db_per_km == declared["absorption_db_per_km"]
            assert sensor.detection_threshold_db == declared["detection_threshold_db"]

        hostage = exp["hostage"]
        assert mission._HOSTAGE_DAYS == hostage["days"]
        assert mission._HOSTAGE_DT == hostage["dt"]
        assert mission._HOSTAGE_ONSET == hostage["onset_threshold"]
        # The rate block, kindness schedule and initial state the adapter runs
        # must be the ones the manuscript declares (§5 Table 2).
        assert mission._HOSTAGE_PARAMS == MV.hostage_params(hostage)
        assert mission._HOSTAGE_EVENTS == MV.kindness_events(hostage)
        assert mission._HOSTAGE_INITIAL == MV.hostage_initial_state(hostage)

        assert mission._GRID_OUTAGE == exp["power_grid"]["initial_outage"]
        assert mission._GRID_OVERLOAD_FACTOR == exp["power_grid"]["overload_factor"]

        neg = exp["negotiation"]
        assert mission._NEGOTIATION.deadline_days == neg["deadline_days"]
        assert mission._NEGOTIATION.negotiator_discount == neg["negotiator_discount"]
        assert mission._NEGOTIATION.concession_rate == neg["concession_rate"]
        assert mission._NEGOTIATION.captor_discount_base == neg["captor_discount_base"]
        assert mission._NEGOTIATION.captor_discount_gain == neg["captor_discount_gain"]
        assert mission._NEGOTIATION.initial_demand == neg["initial_demand"]
        assert mission._NEGOTIATION.initial_offer == neg["initial_offer"]

        fusion = exp["fusion"]
        assert mission._FUSION.dt == fusion["dt"]
        assert mission._FUSION.steps == fusion["steps"]
        assert mission._FUSION.process_noise == fusion["process_noise"]
        assert mission._FUSION.measurement_noise == fusion["measurement_noise"]
        assert mission._FUSION.seed == fusion["seed"]

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

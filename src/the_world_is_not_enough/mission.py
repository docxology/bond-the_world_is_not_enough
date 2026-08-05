"""ELEKTRA — the MissionProvider adapter for *The World Is Not Enough* (1999).

This module is the thin protocol layer that binds the pure domain cores
(:mod:`~the_world_is_not_enough.pipeline_security`,
:mod:`~the_world_is_not_enough.sub_defense`,
:mod:`~the_world_is_not_enough.hostage_psychology`,
:mod:`~the_world_is_not_enough.power_grid`,
:mod:`~the_world_is_not_enough.negotiation_tactics`,
:mod:`~the_world_is_not_enough.sensor_fusion`) to the FROZEN ``bond_api``
mission protocol. It exposes a top-level ``the_world_is_not_enough.mission``
module (per the discovery contract) whose ``MissionProvider`` class satisfies
:class:`bond_api.protocol.MissionProvider`, and registers the domain
capabilities in a :class:`bond_api.registry.GadgetRegistry` at import time.

The domain cores stay importable without ``bond_api``; this module is the only
one that imports the protocol. All mission inputs are fixed module constants,
and the outcome carries full provenance (package version, deterministic seed,
an input hash over the executed plan) with ``wall_time_s = 0.0`` so the mission
is byte-reproducible. The public protocol surface is stable: deeper pillars are
added as extra plan steps, result keys, and gadgets, not as protocol changes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, cast

from bond_api.protocol import (
    Asset,
    Constraint,
    Debrief,
    Finding,
    MissionBrief,
    MissionOutcome,
    MissionPlan,
    Provenance,
    ReconReport,
    ReconRequest,
    Step,
)
from bond_api.registry import GadgetRegistry

from the_world_is_not_enough import (
    hostage_psychology,
    negotiation_tactics,
    pipeline_security,
    power_grid,
    sensor_fusion,
    sub_defense,
)

__all__ = [
    "CODENAME",
    "FILM",
    "GADGETS",
    "PACKAGE_VERSION",
    "SEED",
    "MissionProvider",
    "mission_input_hash",
]

#: Package identity.
FILM = "the_world_is_not_enough"
CODENAME = "ELEKTRA"
SEED = 1999  # the film's release year — the deterministic mission seed
PACKAGE_VERSION = "0.1.0"

# --- Fixed, deterministic mission inputs -------------------------------------
_PIPELINE = pipeline_security.default_pipeline()
_TAMPER_EVENTS = 40
_DETECT_PROB = 0.85

_SUB_GRID = 16
_SUB_STEP_M = 3000.0
_SUB_START: tuple[int, int] = (1, 1)
_SUB_GOAL: tuple[int, int] = (14, 14)
# Passive-sonar parameters are physically plausible for a mid-frequency
# broadband listen: SL 125 dB (target radiated noise), NL 78 dB (moderate sea
# state + self), alpha 0.5 dB/km absorption, operator DT 15 dB.
_SUB_SENSORS: tuple[sub_defense.Sensor, ...] = (
    sub_defense.Sensor(
        x=8,
        y=3,
        source_level=125.0,
        noise_level=78.0,
        absorption_db_per_km=0.5,
        detection_threshold_db=15.0,
    ),
    sub_defense.Sensor(
        x=3,
        y=9,
        source_level=125.0,
        noise_level=78.0,
        absorption_db_per_km=0.5,
        detection_threshold_db=15.0,
    ),
    sub_defense.Sensor(
        x=12,
        y=12,
        source_level=125.0,
        noise_level=78.0,
        absorption_db_per_km=0.5,
        detection_threshold_db=15.0,
    ),
)

_HOSTAGE_DAYS = 30.0
_HOSTAGE_DT = 0.25
_HOSTAGE_ONSET = 0.5
# The ODE rate block, kindness schedule and initial state. These mirror
# `experiment.hostage` in manuscript/config.yaml; the mirroring is asserted by
# tests/test_mission.py::TestExecute::test_every_mirrored_constant_equals_its_config_key.
_HOSTAGE_PARAMS = hostage_psychology.DynamicsParams(
    fear_decay=0.12,
    threat_sensitivity=0.30,
    kindness_gain=0.65,
    gratitude_decay=0.05,
    ident_gain=0.50,
    fear_suppress=0.15,
    threat_initial=0.75,
    threat_decay=0.18,
    threat_floor=0.12,
)
_HOSTAGE_EVENTS = hostage_psychology.DEFAULT_KINDNESS_EVENTS
_HOSTAGE_INITIAL = hostage_psychology.DEFAULT_INITIAL_STATE

_GRID = power_grid.default_power_grid()
_GRID_OUTAGE = "3->5"
_GRID_OVERLOAD_FACTOR = 1.0

_NEGOTIATION = negotiation_tactics.NegotiationParams(
    deadline_days=10.0,
    negotiator_discount=0.90,
    concession_rate=0.08,
    captor_discount_base=0.55,
    captor_discount_gain=0.45,
    initial_demand=0.95,
    initial_offer=0.05,
)

_FUSION = sensor_fusion.TrackConfig(
    dt=1.0,
    steps=20,
    process_noise=0.1,
    measurement_noise=2.0,
    seed=SEED,
)


def _summary_assets() -> tuple[Asset, ...]:
    """Deterministic asset manifests (one per pillar) attached to the brief."""
    return (
        Asset(
            kind="pipeline",
            name="caspian-trunk",
            payload={
                "nodes": _PIPELINE.node_count(),
                "edges": _PIPELINE.edge_count,
                "tamper_events": _TAMPER_EVENTS,
                "detection_probability": _DETECT_PROB,
            },
        ),
        Asset(
            kind="submarine",
            name="sonar-scenario",
            payload={
                "grid": _SUB_GRID,
                "step_m": _SUB_STEP_M,
                "sensors": len(_SUB_SENSORS),
                "start": list(_SUB_START),
                "goal": list(_SUB_GOAL),
            },
        ),
        Asset(
            kind="hostage",
            name="influence-model",
            payload={
                "days": _HOSTAGE_DAYS,
                "dt": _HOSTAGE_DT,
                "onset_threshold": _HOSTAGE_ONSET,
            },
        ),
        Asset(
            kind="power",
            name="caspian-grid",
            payload={
                "buses": _GRID.n_buses,
                "lines": len(_GRID.lines),
                "initial_outage": _GRID_OUTAGE,
            },
        ),
        Asset(
            kind="negotiation",
            name="bargaining-stake",
            payload={
                "deadline_days": _NEGOTIATION.deadline_days,
                "negotiator_discount": _NEGOTIATION.negotiator_discount,
            },
        ),
        Asset(
            kind="fusion",
            name="tracking-scenario",
            payload={
                "steps": _FUSION.steps,
                "measurement_noise": _FUSION.measurement_noise,
                "seed": _FUSION.seed,
            },
        ),
    )


def _plan_params() -> dict[str, Any]:
    """The deterministic parameter map the plan steps execute against."""
    return {
        "tamper_events": _TAMPER_EVENTS,
        "detection_probability": _DETECT_PROB,
        "grid_size": _SUB_GRID,
        "step_m": _SUB_STEP_M,
        "start": list(_SUB_START),
        "goal": list(_SUB_GOAL),
        "hostage_days": _HOSTAGE_DAYS,
        "hostage_dt": _HOSTAGE_DT,
        "hostage_onset": _HOSTAGE_ONSET,
        "power_outage": _GRID_OUTAGE,
        "power_overload_factor": _GRID_OVERLOAD_FACTOR,
        "neg_deadline_days": _NEGOTIATION.deadline_days,
        "fusion_steps": _FUSION.steps,
        "fusion_measurement_noise": _FUSION.measurement_noise,
    }


def mission_input_hash(plan: MissionPlan) -> str:
    """Stable SHA-256 fingerprint of the executed plan and its parameters.

    Deterministic by construction: the canonical form is the sorted JSON of
    ``(step.name, step.action, step.params)`` plus the fixed plan parameters,
    so two executions of the same mission hash identically.
    """
    canonical = json.dumps(
        {
            "steps": [
                {"name": s.name, "action": s.action, "params": s.params}
                for s in plan.steps
            ],
            "params": _plan_params(),
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _run_steps() -> dict[str, Any]:
    """Execute every mission step against the pure domain cores (real math)."""
    # 1. pipeline choke-point analysis
    analysis = cast("dict[str, Any]", pipeline_security.analyze_choke_points(_PIPELINE))
    # 2. tamper simulation
    tamper = cast(
        "dict[str, Any]",
        pipeline_security.simulate_tamper(
            _PIPELINE, _TAMPER_EVENTS, SEED, _DETECT_PROB
        ),
    )
    # 3. passive-sonar risk field
    risk = sub_defense.build_risk_map(_SUB_GRID, _SUB_SENSORS, _SUB_STEP_M)
    # 4. evasion routing (naive vs. least-risk)
    evasion = cast(
        "dict[str, Any]",
        sub_defense.evasion_analysis(risk, start=_SUB_START, goal=_SUB_GOAL),
    )
    # 5. hostage dynamics
    dynamics = hostage_psychology.integrate_dynamics(
        days=_HOSTAGE_DAYS,
        dt=_HOSTAGE_DT,
        onset_threshold=_HOSTAGE_ONSET,
        params=_HOSTAGE_PARAMS,
        events=_HOSTAGE_EVENTS,
        initial_state=_HOSTAGE_INITIAL,
    )
    # 6. power-grid cascading blackout
    blackout = power_grid.cascade_failure(
        _GRID,
        _GRID_OUTAGE,
        overload_factor=_GRID_OVERLOAD_FACTOR,
    )
    # 7. hostage negotiation (syndrome drives the captor's patience)
    settlement = cast(
        "dict[str, Any]",
        negotiation_tactics.settlement_analysis(
            _NEGOTIATION, syndrome=float(dynamics.final_syndrome)
        ),
    )
    # 8. sensor fusion (Kalman track of the hijacked submarine)
    fusion = sensor_fusion.run_tracking(_FUSION)

    choke_points = cast("tuple[str, ...]", analysis["choke_points"])
    return {
        "max_flow_kbpd": float(analysis["max_flow_kbpd"]),
        "min_cut_capacity_kbpd": float(analysis["min_cut_capacity_kbpd"]),
        "choke_point_count": int(analysis["choke_point_count"]),
        "top_choke_point": str(choke_points[0]) if choke_points else "none",
        "sensor_coverage": float(analysis["sensor_coverage"]),
        "tamper_events": tamper["total_events"],
        "tamper_detection_rate": float(tamper["detection_rate"]),
        # A cumulative *volume* (kbbl), not a per-day rate: see
        # pipeline_security.simulate_tamper for the accounting convention.
        "tamper_throughput_lost_kbbl": float(tamper["throughput_lost_kbbl"]),
        "naive_exposure": float(evasion["naive_exposure"]),
        "optimal_exposure": float(evasion["optimal_exposure"]),
        "exposure_reduction": float(evasion["exposure_reduction"]),
        "syndrome_final": float(dynamics.final_syndrome),
        "syndrome_peak": float(dynamics.peak_syndrome),
        "syndrome_onset_day": (
            float(dynamics.onset_day) if dynamics.onset_day is not None else None
        ),
        "influence_ratio": float(dynamics.influence_ratio),
        "blackout_steps": int(blackout["steps"]),
        "blackout_lines_tripped": len(blackout["tripped"]),
        "blackout_lost_load_mw": float(blackout["lost_load_mw"]),
        "blackout_fraction": float(blackout["blackout_fraction"]),
        "neg_reached": bool(settlement["reached"]),
        "neg_settlement_day": (
            float(settlement["settlement_day"])
            if settlement["settlement_day"] is not None
            else None
        ),
        "neg_settlement_split": (
            float(settlement["settlement_split"])
            if settlement["settlement_split"] is not None
            else None
        ),
        "neg_captor_share": float(settlement["captor_share"]),
        "track_filter_rmse": float(fusion["filter_rmse"]),
        "track_measurement_rmse": float(fusion["measurement_rmse"]),
        "track_final_error": float(fusion["final_position_error"]),
        "track_gain": float(fusion["filter_gain"]),
        "track_converged": bool(fusion["converged"]),
    }


class MissionProvider:
    """ELEKTRA: deterministic MissionProvider over the six pillar models."""

    film = FILM

    def brief(self) -> MissionBrief:
        """Declare the ELEKTRA mission and its operational objectives."""
        return MissionBrief(
            film=self.film,
            codename=CODENAME,
            objectives=(
                "interdict tamper at oil-pipeline choke points",
                "contain a coordinated power-grid blackout",
                "route the nuclear submarine to safety and track the hijacked hull",
                "model hostage-captor dynamics and negotiate the captor's patience",
            ),
            assets=_summary_assets(),
            constraints=(
                Constraint(
                    kind="determinism",
                    detail=(
                        f"fixed seed {SEED}; the only stochastic steps (tamper "
                        "simulation, fusion measurement noise) draw from seeded "
                        "generators, so every run is byte-reproducible"
                    ),
                ),
                Constraint(
                    kind="isolation", detail="domain cores importable without bond_api"
                ),
                Constraint(
                    kind="math",
                    detail=(
                        "real algorithms: max-flow/min-cut, Dijkstra, RK4, "
                        "DC power flow, bargaining, Kalman filtering"
                    ),
                ),
            ),
        )

    def recon(self, request: ReconRequest) -> ReconReport:
        """Survey the goal and each pillar's operational surface (measured)."""
        return ReconReport(
            findings=(
                Finding(label="goal", detail=request.goal),
                Finding(
                    label="pipeline",
                    detail=(
                        f"{_PIPELINE.node_count()} nodes, {_PIPELINE.edge_count} segments, "
                        f"{_TAMPER_EVENTS} tamper scenarios"
                    ),
                ),
                Finding(
                    label="submarine",
                    detail=(
                        f"{_SUB_GRID}x{_SUB_GRID} sonar grid, {len(_SUB_SENSORS)} listening sensors"
                    ),
                ),
                Finding(
                    label="hostage",
                    detail=(
                        f"{_HOSTAGE_DAYS:g}-day ODE integration (dt={_HOSTAGE_DT:g}), "
                        f"onset threshold {_HOSTAGE_ONSET:g}"
                    ),
                ),
                Finding(
                    label="power",
                    detail=(
                        f"{_GRID.n_buses} buses, {len(_GRID.lines)} lines, "
                        f"targeted interconnector {_GRID_OUTAGE}"
                    ),
                ),
                Finding(
                    label="negotiation",
                    detail=(
                        f"{_NEGOTIATION.deadline_days:g}-day deadline, "
                        f"negotiator discount {_NEGOTIATION.negotiator_discount:g}"
                    ),
                ),
                Finding(
                    label="fusion",
                    detail=(
                        f"{_FUSION.steps} fixes, measurement std "
                        f"{_FUSION.measurement_noise:g} (seed {_FUSION.seed})"
                    ),
                ),
            )
        )

    def plan(self, brief: MissionBrief) -> MissionPlan:
        """Plan the eight deterministic execution steps."""
        params = _plan_params()
        return MissionPlan(
            steps=(
                Step(
                    name="pipeline",
                    action="analyze_choke_points",
                    params={"objective": brief.objectives[0]},
                ),
                Step(
                    name="pipeline",
                    action="simulate_tamper",
                    params={"events": params["tamper_events"]},
                ),
                Step(
                    name="submarine",
                    action="build_risk_map",
                    params={"grid": params["grid_size"]},
                ),
                Step(
                    name="submarine",
                    action="route_evasion",
                    params={"goal": params["goal"]},
                ),
                Step(
                    name="hostage",
                    action="integrate_dynamics",
                    params={"days": params["hostage_days"]},
                ),
                Step(
                    name="power",
                    action="cascade_blackout",
                    params={"outage": params["power_outage"]},
                ),
                Step(
                    name="negotiation",
                    action="settle_bargaining",
                    params={"deadline": params["neg_deadline_days"]},
                ),
                Step(
                    name="fusion",
                    action="track_submarine",
                    params={"steps": params["fusion_steps"]},
                ),
            )
        )

    def execute(self, plan: MissionPlan) -> MissionOutcome:
        """Run the eight steps and return a measured outcome with full provenance."""
        results = _run_steps()
        results["steps_completed"] = len(plan.steps)
        return MissionOutcome(
            success=True,
            results=results,
            provenance=Provenance(
                package_version=PACKAGE_VERSION,
                seed=SEED,
                input_hash=mission_input_hash(plan),
                wall_time_s=0.0,
            ),
        )

    def debrief(self, outcome: MissionOutcome) -> Debrief:
        """Summarize the mission and derive standing lessons from measured outputs."""
        r = outcome.results
        lessons = [
            (
                f"the global min cut carries {r['min_cut_capacity_kbpd']:.1f} kbbl/day — "
                "guarding that choke point protects the whole corridor"
            ),
            (
                f"least-risk routing cut exposed detection probability by "
                f"{r['exposure_reduction'] * 100.0:.1f}% over line-of-sight"
            ),
            (
                f"taking the {_GRID_OUTAGE} interconnector blacked "
                f"{r['blackout_lost_load_mw']:.0f} MW "
                f"({r['blackout_fraction'] * 100.0:.1f}% of load) via a "
                f"{r['blackout_lines_tripped']}-line cascade"
            ),
            (
                f"hostage identification reached S={r['syndrome_final']:.2f}, lifting the "
                f"captor's bargaining claim to {r['neg_captor_share'] * 100.0:.1f}% of the stake"
            ),
            (
                f"Kalman fusion cut track RMSE from {r['track_measurement_rmse']:.2f} to "
                f"{r['track_filter_rmse']:.2f} ({r['track_gain'] * 100.0:.1f}% gain) over the fixes"
            ),
            f"deterministic provenance (seed {SEED}, wall_time 0) makes every result auditable",
        ]
        return Debrief(outcome=outcome, lessons=tuple(lessons))


def _build_gadgets() -> GadgetRegistry:
    """Build and register the ELEKTRA gadget surface (six domain capabilities)."""
    registry = GadgetRegistry()
    registry.register(
        FILM,
        {
            "pipeline_analysis": pipeline_security.analyze_choke_points,
            "tamper_simulation": pipeline_security.simulate_tamper,
            "evasion_analysis": sub_defense.evasion_analysis,
            "hostage_dynamics": hostage_psychology.integrate_dynamics,
            "power_cascade": power_grid.cascade_failure,
            "negotiation_settlement": negotiation_tactics.settlement_analysis,
            "submarine_tracking": sensor_fusion.run_tracking,
            "mission_input_hash": mission_input_hash,
        },
    )
    return registry


#: The package's gadget registry, populated at import for the orchestrator.
GADGETS: GadgetRegistry = _build_gadgets()

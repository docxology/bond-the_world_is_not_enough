"""Manuscript variable hydration for ELEKTRA (the_world_is_not_enough).

Every ``{{TOKEN}}`` in ``manuscript/*.md`` resolves through
:func:`generate_variables`, which reads ``manuscript/config.yaml`` and then
*runs the deterministic domain models* to compute the result tokens. Metrics
are never hand-authored in prose: they flow through this module so the
manuscript cannot drift from the code.

No token reads a wall clock. The one time-valued token,
``MANUSCRIPT_EDITION_STAMP``, is derived from the committed ``paper.date`` key
(see :func:`edition_stamp`), so regenerating the artifacts is byte-identical —
the property §6 of the manuscript claims and
``tests/test_manuscript_variables.py::TestRegenerationDeterminism`` enforces by
regenerating twice across a second boundary and diffing the persisted bytes.

The consuming orchestrator is ``scripts/z_generate_manuscript_variables.py``
(thin wrapper); the live cross-reference gate lives in
``tests/test_manuscript_variables.py``.
"""

from __future__ import annotations

import datetime as _dt
import math
import platform
import re
from dataclasses import dataclass as _dc
from pathlib import Path
from typing import Any, cast

import yaml

from the_world_is_not_enough import (
    hostage_psychology,
    negotiation_tactics,
    pipeline_security,
    power_grid,
    sensor_fusion,
    sub_defense,
)

__all__ = [
    "DECLARED_CONFIG_TOKENS",
    "DERIVED_DATASET_TOKENS",
    "MISSION_CODENAME",
    "MISSION_FILM",
    "RESULT_TOKEN_UNITS",
    "build_mission_scenario",
    "edition_stamp",
    "generate_variables",
    "hostage_initial_state",
    "hostage_params",
    "kindness_events",
    "load_manuscript_config",
    "resolve_manuscript_tree",
]

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "manuscript" / "config.yaml"

#: Physical unit of every ``RESULT_*`` token, declared once so prose, ledger
#: and tests cannot disagree about what a number means. The distinction that
#: matters is *rate* (``kbbl/day``, ``MW``) versus *volume* (``kbbl``): a rate
#: is bounded by the corridor's installed capacity, a cumulative volume is not.
#: ``""`` marks a dimensionless or categorical token.
RESULT_TOKEN_UNITS: dict[str, str] = {
    "RESULT_MAX_FLOW": "kbbl/day",
    "RESULT_MIN_CUT_CAPACITY": "kbbl/day",
    "RESULT_CHOKE_POINT_COUNT": "",
    "RESULT_TOP_CHOKE_POINT": "",
    "RESULT_SENSOR_COVERAGE": "percent",
    "RESULT_TAMPER_EVENTS": "",
    "RESULT_TAMPER_DETECTION_RATE": "percent",
    "RESULT_TAMPER_THROUGHPUT_LOST": "kbbl",
    "RESULT_TAMPER_DOWNTIME_DAYS": "days",
    "RESULT_SUB_SENSORS": "",
    "RESULT_NAIVE_EXPOSURE": "",
    "RESULT_OPTIMAL_EXPOSURE": "",
    "RESULT_EXPOSURE_REDUCTION": "percent",
    "RESULT_SYNDROME_FINAL": "",
    "RESULT_SYNDROME_PEAK": "",
    "RESULT_SYNDROME_ONSET_DAY": "days",
    "RESULT_INFLUENCE_RATIO": "",
    "RESULT_BLACKOUT_STEPS": "",
    "RESULT_BLACKOUT_LINES_TRIPPED": "",
    "RESULT_BLACKOUT_LOST_MW": "MW",
    "RESULT_BLACKOUT_FRACTION": "",
    "RESULT_NEG_SETTLEMENT_DAY": "days",
    "RESULT_NEG_SETTLEMENT_SPLIT": "",
    "RESULT_NEG_CAPTOR_SHARE": "",
    "RESULT_NEG_BASELINE_SHARE": "",
    "RESULT_NEG_CAPTOR_LEVERAGE_PCT": "percent",
    "RESULT_TRACK_RMSE": "",
    "RESULT_TRACK_MEASUREMENT_RMSE": "",
    "RESULT_TRACK_FINAL_ERROR": "",
    "RESULT_TRACK_GAIN": "percent",
}

#: ``CONFIG_*`` tokens whose value is *typed by the author* in
#: ``manuscript/config.yaml``. Editing the file changes them.
DECLARED_CONFIG_TOKENS: frozenset[str] = frozenset(
    {
        "CONFIG_SEED",
        "CONFIG_TAMPER_EVENTS",
        "CONFIG_DETECTION_PROBABILITY",
        "CONFIG_SUB_GRID",
        "CONFIG_SUB_STEP_KM",
        "CONFIG_SUB_SENSORS",
        "CONFIG_HOSTAGE_DAYS",
        "CONFIG_HOSTAGE_DT",
        "CONFIG_HOSTAGE_ONSET",
        "CONFIG_HOSTAGE_INITIAL_STATE",
        "CONFIG_HOSTAGE_FEAR_DECAY",
        "CONFIG_HOSTAGE_THREAT_SENSITIVITY",
        "CONFIG_HOSTAGE_KINDNESS_GAIN",
        "CONFIG_HOSTAGE_GRATITUDE_DECAY",
        "CONFIG_HOSTAGE_IDENT_GAIN",
        "CONFIG_HOSTAGE_FEAR_SUPPRESS",
        "CONFIG_HOSTAGE_THREAT_INITIAL",
        "CONFIG_HOSTAGE_THREAT_DECAY",
        "CONFIG_HOSTAGE_THREAT_FLOOR",
        "CONFIG_HOSTAGE_KINDNESS_SCHEDULE",
        "CONFIG_GRID_INITIAL_OUTAGE",
        "CONFIG_NEG_DEADLINE_DAYS",
        "CONFIG_NEG_NEGOTIATOR_DISCOUNT",
        "CONFIG_NEG_CONCESSION_RATE",
        "CONFIG_NEG_CAPTOR_DISCOUNT_BASE",
        "CONFIG_NEG_CAPTOR_DISCOUNT_GAIN",
        "CONFIG_NEG_INITIAL_DEMAND",
        "CONFIG_NEG_INITIAL_OFFER",
        "CONFIG_FUSION_STEPS",
        "CONFIG_FUSION_MEASUREMENT_NOISE",
    }
)

#: ``CONFIG_*`` tokens *derived from a fixed dataset or module constant*.
#: Editing ``manuscript/config.yaml`` cannot change them; changing the module
#: dataset can. The manuscript must label these as derived, never as tunable.
DERIVED_DATASET_TOKENS: frozenset[str] = frozenset(
    {
        "CONFIG_PIPELINE_NODES",
        "CONFIG_PIPELINE_SEGMENTS",
        "CONFIG_CHOKE_UTILIZATION",
        "CONFIG_GRID_BUSES",
        "CONFIG_GRID_LINES",
        "CONFIG_GRID_LOAD_MW",
        "CONFIG_GRID_STRONG_TIE_MW",
        "CONFIG_GRID_WEAK_TIE",
        "CONFIG_GRID_WEAK_TIE_MW",
    }
)

MISSION_CODENAME = "ELEKTRA"
MISSION_FILM = "The World Is Not Enough (1999)"
PACKAGE_VERSION = "0.1.0"

_TOKEN_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")


def load_manuscript_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate ``manuscript/config.yaml`` (or an explicit path)."""
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    if not path.is_file():
        raise FileNotFoundError(f"manuscript config not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise TypeError(
            f"manuscript config must be a top-level mapping, got {type(data).__name__}"
        )
    return data


def _fmt(value: float, precision: int = 3) -> str:
    return f"{value:.{precision}f}"


_HOSTAGE_RATE_NAMES = (
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


#: Keys consumed by the shared scenario builder (dotted ``where.key`` form),
#: recorded by :func:`_require` during :func:`build_mission_scenario` and
#: asserted against the config's every leaf by tests (the completeness half of
#: the config<>adapter contract — see ``test_the_scenario_consumes_every_config_leaf``).
_CONSUMED_CONFIG_KEYS: set[str] = set()


def _require(mapping: dict[Any, Any], key: str, where: str) -> Any:
    """Fail-closed config read: a missing ``key`` raises instead of defaulting.

    The accessor used where the manuscript claims a value is *typed in
    ``config.yaml``*. A silently-implicit default would let a maintainer delete
    a knob and change nothing while the manuscript still claimed it was
    consumed — exactly the fail-open hole this round closes.
    """
    _CONSUMED_CONFIG_KEYS.add(f"{where}.{key}")
    try:
        return mapping[key]
    except (KeyError, IndexError, TypeError) as exc:
        raise KeyError(
            f"missing required config key {key!r} in {where} — it is typed in "
            "manuscript/config.yaml and consumed by the model; delete it only "
            "on purpose"
        ) from exc


def hostage_params(hostage_cfg: dict[str, Any]) -> hostage_psychology.DynamicsParams:
    """Build the ODE rate block from ``experiment.hostage.dynamics``.

    Fails *closed*: every one of the nine rates is required. Deleting one
    raises ``KeyError`` rather than silently falling back to a module default,
    so ``manuscript/config.yaml`` is the single authority and a deleted knob
    cannot pass unnoticed (C2).
    """
    rates = hostage_cfg.get("dynamics", {}) or {}
    if not isinstance(rates, dict):
        raise TypeError("experiment.hostage.dynamics must be a mapping")
    values = {
        name: float(_require(rates, name, "experiment.hostage.dynamics"))
        for name in _HOSTAGE_RATE_NAMES
    }
    return hostage_psychology.DynamicsParams(**values)


def kindness_events(
    hostage_cfg: dict[str, Any],
) -> tuple[hostage_psychology.KindnessEvent, ...]:
    """Build the small-kindness impulse train from ``experiment.hostage``.

    Fails *closed* when the schedule is absent (it is typed in
    ``manuscript/config.yaml``).
    """
    raw = _require(hostage_cfg, "kindness_events", "experiment.hostage")
    if not isinstance(raw, list):
        raise TypeError("experiment.hostage.kindness_events must be a list")
    return tuple(
        hostage_psychology.KindnessEvent(
            day=float(_require(item, "day", "experiment.hostage.kindness_events")),
            magnitude=float(
                _require(item, "magnitude", "experiment.hostage.kindness_events")
            ),
        )
        for item in raw
    )


def hostage_initial_state(
    hostage_cfg: dict[str, Any],
) -> tuple[float, float, float]:
    """Read the initial ``(fear, gratitude, identification)`` state.

    Fails *closed* when the initial state is absent (it is typed in
    ``manuscript/config.yaml``).
    """
    raw = _require(hostage_cfg, "initial_state", "experiment.hostage")
    if not isinstance(raw, list) or len(raw) != 3:
        raise TypeError(
            "experiment.hostage.initial_state must be a list of three fractions"
        )
    return (float(raw[0]), float(raw[1]), float(raw[2]))


@_dc(frozen=True)
class MissionScenario:
    """Every *tunable* mission input, resolved once from ``manuscript/config.yaml``.

    The single source of truth for both the manuscript and the mission adapter:
    :func:`mission.MissionProvider` and :func:`_run_domain_tokens` both consume
    this, so editing a knob in ``manuscript/config.yaml`` moves the mission, the
    figures, and the manuscript token together. Building it fails *closed*: a
    deleted or mis-typed key raises rather than silently defaulting.
    """

    seed: int
    tamper_events: int
    detection_probability: float
    submarine_grid: int
    submarine_step_m: float
    submarine_start: tuple[int, int]
    submarine_goal: tuple[int, int]
    submarine_sensors: tuple[sub_defense.Sensor, ...]
    hostage_days: float
    hostage_dt: float
    hostage_onset: float
    hostage_params: hostage_psychology.DynamicsParams
    hostage_events: tuple[hostage_psychology.KindnessEvent, ...]
    hostage_initial: tuple[float, float, float]
    grid_outage: str
    grid_overload_factor: float
    negotiation_params: negotiation_tactics.NegotiationParams
    fusion_config: sensor_fusion.TrackConfig


def _experiment_block(config: dict[str, Any]) -> dict[str, Any]:
    """The ``experiment`` section, resolving it fail-closed from the config."""
    if "experiment" not in config:
        raise KeyError(
            "manuscript config is missing the 'experiment' block — the mission "
            "and manuscript both consume it; a deleted block is a defect"
        )
    experiment = config["experiment"]
    if not isinstance(experiment, dict):
        raise TypeError("manuscript config 'experiment' section must be a mapping")
    return experiment


def build_mission_scenario(
    config: dict[str, Any] | None = None,
) -> MissionScenario:
    """Resolve every tunable mission input from the config (fail-closed).

    Reads ``manuscript/config.yaml`` (or an explicit config dict) and, for each
    input the mission and manuscript share, *requires* the declared key rather
    than defaulting. The only non-tunable datasets (the pipeline graph and the
    power grid) come from their module datasets and are **not** read here, in
    keeping with the declared/derived partition §5 of the manuscript draws.
    """
    _CONSUMED_CONFIG_KEYS.clear()
    loaded = load_manuscript_config() if config is None else config
    experiment = _experiment_block(loaded)
    seed = int(_require(experiment, "seed", "experiment"))

    pipeline_cfg = _require(experiment, "pipeline", "experiment")
    if not isinstance(pipeline_cfg, dict):
        raise TypeError("experiment.pipeline must be a mapping")
    tamper_events = int(_require(pipeline_cfg, "tamper_events", "experiment.pipeline"))
    detection_probability = float(
        _require(pipeline_cfg, "detection_probability", "experiment.pipeline")
    )

    submarine_cfg = _require(experiment, "submarine", "experiment")
    if not isinstance(submarine_cfg, dict):
        raise TypeError("experiment.submarine must be a mapping")
    grid_size = int(_require(submarine_cfg, "grid_size", "experiment.submarine"))
    step_m = float(_require(submarine_cfg, "step_m", "experiment.submarine"))
    raw_start = _require(submarine_cfg, "start", "experiment.submarine")
    raw_goal = _require(submarine_cfg, "goal", "experiment.submarine")
    if len(raw_start) != 2 or len(raw_goal) != 2:
        raise TypeError("experiment.submarine start/goal must be (x, y) pairs")
    start = (int(raw_start[0]), int(raw_start[1]))
    goal = (int(raw_goal[0]), int(raw_goal[1]))
    raw_sensors = _require(submarine_cfg, "sensors", "experiment.submarine")
    sensors = tuple(
        sub_defense.Sensor(
            x=int(_require(s, "x", "experiment.submarine.sensors")),
            y=int(_require(s, "y", "experiment.submarine.sensors")),
            source_level=float(
                _require(s, "source_level", "experiment.submarine.sensors")
            ),
            noise_level=float(
                _require(s, "noise_level", "experiment.submarine.sensors")
            ),
            absorption_db_per_km=float(
                _require(s, "absorption_db_per_km", "experiment.submarine.sensors")
            ),
            detection_threshold_db=float(
                _require(s, "detection_threshold_db", "experiment.submarine.sensors")
            ),
        )
        for s in raw_sensors
    )

    hostage_cfg = _require(experiment, "hostage", "experiment")
    if not isinstance(hostage_cfg, dict):
        raise TypeError("experiment.hostage must be a mapping")
    hostage_days = float(_require(hostage_cfg, "days", "experiment.hostage"))
    hostage_dt = float(_require(hostage_cfg, "dt", "experiment.hostage"))
    hostage_onset = float(
        _require(hostage_cfg, "onset_threshold", "experiment.hostage")
    )

    power_cfg = _require(experiment, "power_grid", "experiment")
    if not isinstance(power_cfg, dict):
        raise TypeError("experiment.power_grid must be a mapping")
    outage = str(_require(power_cfg, "initial_outage", "experiment.power_grid"))
    overload_factor = float(
        _require(power_cfg, "overload_factor", "experiment.power_grid")
    )

    negotiation_cfg = _require(experiment, "negotiation", "experiment")
    if not isinstance(negotiation_cfg, dict):
        raise TypeError("experiment.negotiation must be a mapping")
    negotiation = negotiation_tactics.NegotiationParams(
        deadline_days=float(
            _require(negotiation_cfg, "deadline_days", "experiment.negotiation")
        ),
        negotiator_discount=float(
            _require(negotiation_cfg, "negotiator_discount", "experiment.negotiation")
        ),
        concession_rate=float(
            _require(negotiation_cfg, "concession_rate", "experiment.negotiation")
        ),
        captor_discount_base=float(
            _require(negotiation_cfg, "captor_discount_base", "experiment.negotiation")
        ),
        captor_discount_gain=float(
            _require(negotiation_cfg, "captor_discount_gain", "experiment.negotiation")
        ),
        initial_demand=float(
            _require(negotiation_cfg, "initial_demand", "experiment.negotiation")
        ),
        initial_offer=float(
            _require(negotiation_cfg, "initial_offer", "experiment.negotiation")
        ),
    )

    fusion_cfg = _require(experiment, "fusion", "experiment")
    if not isinstance(fusion_cfg, dict):
        raise TypeError("experiment.fusion must be a mapping")
    fusion = sensor_fusion.TrackConfig(
        dt=float(_require(fusion_cfg, "dt", "experiment.fusion")),
        steps=int(_require(fusion_cfg, "steps", "experiment.fusion")),
        process_noise=float(_require(fusion_cfg, "process_noise", "experiment.fusion")),
        measurement_noise=float(
            _require(fusion_cfg, "measurement_noise", "experiment.fusion")
        ),
        seed=int(_require(fusion_cfg, "seed", "experiment.fusion")),
    )

    return MissionScenario(
        seed=seed,
        tamper_events=tamper_events,
        detection_probability=detection_probability,
        submarine_grid=grid_size,
        submarine_step_m=step_m,
        submarine_start=start,
        submarine_goal=goal,
        submarine_sensors=sensors,
        hostage_days=hostage_days,
        hostage_dt=hostage_dt,
        hostage_onset=hostage_onset,
        hostage_params=hostage_params(hostage_cfg),
        hostage_events=kindness_events(hostage_cfg),
        hostage_initial=hostage_initial_state(hostage_cfg),
        grid_outage=outage,
        grid_overload_factor=overload_factor,
        negotiation_params=negotiation,
        fusion_config=fusion,
    )


def _run_domain_tokens(config: dict[str, Any]) -> dict[str, str]:
    """Measure the three pillar models and format their result tokens."""
    experiment = config.get("experiment", {}) or {}
    if not isinstance(experiment, dict):
        raise TypeError("manuscript config 'experiment' section must be a mapping")
    seed = int(experiment.get("seed", 1999))

    # --- pipeline pillar ---
    network = pipeline_security.default_pipeline()
    analysis = cast("dict[str, Any]", pipeline_security.analyze_choke_points(network))
    pipeline_cfg = experiment.get("pipeline", {}) or {}
    tamper_events = int(pipeline_cfg.get("tamper_events", 40))
    detect_prob = float(pipeline_cfg.get("detection_probability", 0.85))
    tamper = cast(
        "dict[str, Any]",
        pipeline_security.simulate_tamper(network, tamper_events, seed, detect_prob),
    )
    choke_points = cast("tuple[str, ...]", analysis["choke_points"])
    top_choke = choke_points[0] if choke_points else "none"

    # --- submarine pillar ---
    submarine_cfg = experiment.get("submarine", {}) or {}
    grid_size = int(submarine_cfg.get("grid_size", 16))
    step_m = float(submarine_cfg.get("step_m", 1000.0))
    raw_start = cast("list[int]", submarine_cfg.get("start", [1, 1]))
    raw_goal = cast("list[int]", submarine_cfg.get("goal", [14, 14]))
    start = (raw_start[0], raw_start[1])
    goal = (raw_goal[0], raw_goal[1])
    raw_sensors = cast("list[dict[str, Any]]", submarine_cfg.get("sensors", []))
    sensors = tuple(
        sub_defense.Sensor(
            x=int(s["x"]),
            y=int(s["y"]),
            source_level=float(s.get("source_level", 150.0)),
            noise_level=float(s.get("noise_level", 65.0)),
            absorption_db_per_km=float(s.get("absorption_db_per_km", 0.05)),
            detection_threshold_db=float(s.get("detection_threshold_db", 10.0)),
        )
        for s in raw_sensors
    )
    risk = sub_defense.build_risk_map(grid_size, sensors, step_m)
    evasion = cast(
        "dict[str, Any]",
        sub_defense.evasion_analysis(
            risk,
            start=start,
            goal=goal,
        ),
    )

    # --- hostage pillar ---
    hostage_cfg = experiment.get("hostage", {}) or {}
    dynamics = hostage_psychology.integrate_dynamics(
        days=float(hostage_cfg.get("days", 30.0)),
        dt=float(hostage_cfg.get("dt", 0.25)),
        onset_threshold=float(hostage_cfg.get("onset_threshold", 0.5)),
        params=hostage_params(hostage_cfg),
        events=kindness_events(hostage_cfg),
        initial_state=hostage_initial_state(hostage_cfg),
    )

    # --- power-grid pillar (cascading blackout) ---
    power_cfg = experiment.get("power_grid", {}) or {}
    grid = power_grid.default_power_grid()
    outage = str(power_cfg.get("initial_outage", "3->5"))
    overload_factor = float(power_cfg.get("overload_factor", 1.0))
    blackout = power_grid.cascade_failure(grid, outage, overload_factor=overload_factor)

    # --- negotiation pillar (hostage syndrome drives the captor's patience) ---
    neg_cfg = experiment.get("negotiation", {}) or {}
    negotiation = negotiation_tactics.NegotiationParams(
        deadline_days=float(neg_cfg.get("deadline_days", 10.0)),
        negotiator_discount=float(neg_cfg.get("negotiator_discount", 0.90)),
        concession_rate=float(neg_cfg.get("concession_rate", 0.08)),
        captor_discount_base=float(neg_cfg.get("captor_discount_base", 0.55)),
        captor_discount_gain=float(neg_cfg.get("captor_discount_gain", 0.45)),
        initial_demand=float(neg_cfg.get("initial_demand", 0.95)),
        initial_offer=float(neg_cfg.get("initial_offer", 0.05)),
    )
    settlement = cast(
        "dict[str, Any]",
        negotiation_tactics.settlement_analysis(
            negotiation, syndrome=float(dynamics.final_syndrome)
        ),
    )
    baseline = negotiation_tactics.equilibrium_shares(
        negotiation.captor_discount_base, negotiation.negotiator_discount
    )[0]
    captor_share = float(settlement["captor_share"])
    # *Relative* increase over the no-syndrome baseline, reported as a percent
    # (like its sibling relative tokens RESULT_EXPOSURE_REDUCTION and
    # RESULT_TRACK_GAIN) so it can never be misread as an absolute pie share.
    leverage = (captor_share - baseline) / baseline if baseline > 0 else 0.0

    # --- sensor-fusion pillar (Kalman track of the hijacked submarine) ---
    fusion_cfg = experiment.get("fusion", {}) or {}
    tracking = sensor_fusion.TrackConfig(
        dt=float(fusion_cfg.get("dt", 1.0)),
        steps=int(fusion_cfg.get("steps", 20)),
        process_noise=float(fusion_cfg.get("process_noise", 0.1)),
        measurement_noise=float(fusion_cfg.get("measurement_noise", 2.0)),
        seed=int(fusion_cfg.get("seed", seed)),
    )
    fusion = sensor_fusion.run_tracking(tracking)

    sensor_count = len(sensors)
    return {
        "RESULT_MAX_FLOW": _fmt(float(analysis["max_flow_kbpd"])),
        "RESULT_MIN_CUT_CAPACITY": _fmt(float(analysis["min_cut_capacity_kbpd"])),
        "RESULT_CHOKE_POINT_COUNT": str(int(analysis["choke_point_count"])),
        "RESULT_TOP_CHOKE_POINT": str(top_choke),
        "RESULT_SENSOR_COVERAGE": _fmt(float(analysis["sensor_coverage"]) * 100.0),
        "RESULT_TAMPER_EVENTS": str(int(tamper["total_events"])),
        "RESULT_TAMPER_DETECTION_RATE": _fmt(float(tamper["detection_rate"]) * 100.0),
        "RESULT_TAMPER_THROUGHPUT_LOST": _fmt(float(tamper["throughput_lost_kbbl"])),
        "RESULT_TAMPER_DOWNTIME_DAYS": _fmt(float(tamper["nominal_downtime_days"]), 1),
        "RESULT_SUB_SENSORS": str(sensor_count),
        "RESULT_NAIVE_EXPOSURE": _fmt(float(evasion["naive_exposure"])),
        "RESULT_OPTIMAL_EXPOSURE": _fmt(float(evasion["optimal_exposure"])),
        "RESULT_EXPOSURE_REDUCTION": _fmt(float(evasion["exposure_reduction"]) * 100.0),
        "RESULT_SYNDROME_FINAL": _fmt(float(dynamics.final_syndrome)),
        "RESULT_SYNDROME_PEAK": _fmt(float(dynamics.peak_syndrome)),
        "RESULT_SYNDROME_ONSET_DAY": (
            _fmt(float(dynamics.onset_day))
            if dynamics.onset_day is not None
            else "not reached"
        ),
        "RESULT_INFLUENCE_RATIO": _fmt(float(dynamics.influence_ratio)),
        "RESULT_BLACKOUT_STEPS": str(int(blackout["steps"])),
        "RESULT_BLACKOUT_LINES_TRIPPED": str(len(blackout["tripped"])),
        "RESULT_BLACKOUT_LOST_MW": _fmt(float(blackout["lost_load_mw"])),
        "RESULT_BLACKOUT_FRACTION": _fmt(float(blackout["blackout_fraction"])),
        "RESULT_NEG_SETTLEMENT_DAY": (
            _fmt(float(settlement["settlement_day"]))
            if settlement["settlement_day"] is not None
            else "not reached"
        ),
        "RESULT_NEG_SETTLEMENT_SPLIT": (
            _fmt(float(settlement["settlement_split"]))
            if settlement["settlement_split"] is not None
            else "none"
        ),
        "RESULT_NEG_CAPTOR_SHARE": _fmt(captor_share),
        "RESULT_NEG_BASELINE_SHARE": _fmt(baseline),
        "RESULT_NEG_CAPTOR_LEVERAGE_PCT": _fmt(leverage * 100.0),
        "RESULT_TRACK_RMSE": _fmt(float(fusion["filter_rmse"])),
        "RESULT_TRACK_MEASUREMENT_RMSE": _fmt(float(fusion["measurement_rmse"])),
        "RESULT_TRACK_FINAL_ERROR": _fmt(float(fusion["final_position_error"])),
        "RESULT_TRACK_GAIN": _fmt(float(fusion["filter_gain"]) * 100.0),
    }


#: Sentinel strings a domain token is allowed to carry when a model genuinely
#: has no value to report (e.g. an onset that never occurs).
_ALLOWED_SENTINELS = frozenset({"not reached", "none"})


def _assert_measurable(result_tokens: dict[str, str]) -> None:
    """Fail loudly when a ``RESULT_*`` token is empty or non-finite.

    This is the strict-mode gate. It is *not* satisfiable by construction: a
    model that returns ``nan``/``inf`` (a singular solve, a divide-by-zero
    normalisation) formats to ``"nan"``/``"inf"`` and is rejected here rather
    than being rendered into the manuscript as a measured result.

    Raises:
        ValueError: if the model run produced no tokens, or a token is blank
            or carries a non-finite numeric value.
    """
    if not result_tokens:
        raise ValueError(
            "domain models produced no result tokens — cannot hydrate manuscript"
        )
    for name, value in sorted(result_tokens.items()):
        text = value.strip()
        if not text:
            raise ValueError(f"manuscript token {name} resolved to an empty value")
        if text in _ALLOWED_SENTINELS:
            continue
        try:
            numeric = float(text)
        except ValueError:
            continue  # a categorical token (e.g. a segment id) — nothing to check
        if not math.isfinite(numeric):
            raise ValueError(
                f"manuscript token {name} resolved to a non-finite value {text!r}"
            )


def _assert_units_consistent(result_tokens: dict[str, str]) -> None:
    """Reject a ``RESULT_*`` token whose value contradicts its declared unit.

    Two checks, both able to fail on real model output:

    1. Every result token must declare a unit in :data:`RESULT_TOKEN_UNITS`, so
       a new number cannot enter the manuscript unlabelled.
    2. A token declared as a **rate** must respect the physical ceiling of the
       system it describes — installed pipeline capacity for ``kbbl/day``,
       connected load for ``MW``. This is the gate that catches a cumulative
       *volume* being rendered as a per-day rate.

    Raises:
        ValueError: on an undeclared unit or a rate above its physical ceiling.
    """
    undeclared = sorted(set(result_tokens) - set(RESULT_TOKEN_UNITS))
    if undeclared:
        raise ValueError(
            f"result tokens without a declared unit in RESULT_TOKEN_UNITS: {undeclared}"
        )
    ceilings = {
        "kbbl/day": sum(e.capacity for e in pipeline_security.default_pipeline().edges),
        "MW": power_grid.total_load(power_grid.default_power_grid()),
    }
    for name, value in sorted(result_tokens.items()):
        ceiling = ceilings.get(RESULT_TOKEN_UNITS[name])
        if ceiling is None:
            continue
        try:
            numeric = float(value)
        except ValueError:
            continue
        if numeric > ceiling:
            raise ValueError(
                f"manuscript token {name} is declared "
                f"{RESULT_TOKEN_UNITS[name]!r} but its value {value} exceeds the "
                f"physical ceiling {ceiling:g} — it is not a rate"
            )


def edition_stamp(paper: dict[str, Any]) -> str:
    """The manuscript edition stamp, derived from the committed ``paper.date``.

    This is deliberately **not** a wall clock. Every artifact this module
    persists — ``output/data/manuscript_variables.json`` and the resolved
    ``output/manuscript/`` tree — is covered by the byte-identity claim in §6
    of the manuscript, so the one time-valued token has to come from a
    committed source that a maintainer edits on purpose. A wall clock here
    silently falsified that claim on every regeneration.

    Args:
        paper: The ``paper`` mapping from ``manuscript/config.yaml``.

    Returns the date rendered as a UTC ISO-8601 instant at midnight.

    Raises:
        KeyError: if ``paper.date`` is absent — fail closed rather than
            defaulting, so a deleted key cannot pass unnoticed.
        ValueError: if ``paper.date`` is not an ISO ``YYYY-MM-DD`` date.
    """
    raw = paper.get("date")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise KeyError(
            "manuscript config 'paper.date' is required — it is the source of "
            "the manuscript edition stamp, which must never be a wall clock"
        )
    if isinstance(raw, _dt.datetime):
        date = raw.date()
    elif isinstance(raw, _dt.date):
        date = raw
    else:
        date = _dt.date.fromisoformat(str(raw).strip())
    return _dt.datetime(
        date.year, date.month, date.day, tzinfo=_dt.timezone.utc
    ).isoformat(timespec="seconds")


def generate_variables(
    *,
    config_path: str | Path | None = None,
    require_outputs: bool = True,
) -> dict[str, str]:
    """Compute the ``{{TOKEN}}`` → value mapping for the manuscript.

    The mapping is a pure function of ``manuscript/config.yaml``, the
    deterministic domain models and the interpreter version: no clock, no
    network, no other ambient state. Two calls in one checkout on one
    interpreter return equal dictionaries.

    Args:
        config_path: Override for ``manuscript/config.yaml``.
        require_outputs: When True (default), the domain models must run and
            produce measureable outputs (always satisfied by construction).

    Returns a mapping of every manuscript token to its resolved string value.
    """
    config = load_manuscript_config(config_path)
    paper = config.get("paper", {})
    if not isinstance(paper, dict):
        raise TypeError("manuscript config 'paper' section must be a mapping")

    result_tokens = _run_domain_tokens(config)
    if require_outputs:
        _assert_measurable(result_tokens)
    _assert_units_consistent(result_tokens)

    return {
        "MISSION_TITLE": str(paper.get("title", "")),
        "MISSION_SUBTITLE": str(paper.get("subtitle", "")),
        "MISSION_FILM": MISSION_FILM,
        "MISSION_CODENAME": MISSION_CODENAME,
        "PACKAGE_VERSION": str(paper.get("version", PACKAGE_VERSION)),
        "PYTHON_VERSION": platform.python_version(),
        "MANUSCRIPT_EDITION_STAMP": edition_stamp(paper),
        **_config_tokens(config),
        **result_tokens,
    }


def _config_tokens(config: dict[str, Any]) -> dict[str, str]:
    """All ``CONFIG_*`` tokens: the declared block plus the derived block.

    The two halves are kept apart deliberately — see
    :data:`DECLARED_CONFIG_TOKENS` and :data:`DERIVED_DATASET_TOKENS`. Only the
    first responds to edits of ``manuscript/config.yaml``; conflating them is
    what made §5 of the manuscript overclaim its tunable surface.
    """
    return {**_declared_config_tokens(config), **_derived_dataset_tokens(config)}


def _declared_config_tokens(config: dict[str, Any]) -> dict[str, str]:
    """``CONFIG_*`` tokens typed by the author in ``manuscript/config.yaml``."""
    experiment = config.get("experiment", {}) or {}
    if not isinstance(experiment, dict):
        raise TypeError("manuscript config 'experiment' section must be a mapping")
    pipeline = experiment.get("pipeline", {}) or {}
    submarine = experiment.get("submarine", {}) or {}
    hostage = experiment.get("hostage", {}) or {}
    power = experiment.get("power_grid", {}) or {}
    negotiation = experiment.get("negotiation", {}) or {}
    fusion = experiment.get("fusion", {}) or {}
    sensors = submarine.get("sensors", []) or []
    rates = hostage_params(hostage)
    events = kindness_events(hostage)
    initial = hostage_initial_state(hostage)
    tokens = {
        "CONFIG_SEED": str(experiment.get("seed", 1999)),
        "CONFIG_TAMPER_EVENTS": str(int(pipeline.get("tamper_events", 40))),
        "CONFIG_DETECTION_PROBABILITY": _fmt(
            float(pipeline.get("detection_probability", 0.85))
        ),
        "CONFIG_SUB_GRID": str(int(submarine.get("grid_size", 16))),
        "CONFIG_SUB_STEP_KM": _fmt(float(submarine.get("step_m", 3000.0)) / 1000.0, 0),
        "CONFIG_SUB_SENSORS": str(len(sensors)),
        "CONFIG_HOSTAGE_DAYS": _fmt(float(hostage.get("days", 30.0)), 1),
        "CONFIG_HOSTAGE_DT": _fmt(float(hostage.get("dt", 0.25))),
        "CONFIG_HOSTAGE_ONSET": _fmt(float(hostage.get("onset_threshold", 0.5))),
        "CONFIG_HOSTAGE_INITIAL_STATE": ", ".join(_fmt(v, 2) for v in initial),
        "CONFIG_HOSTAGE_FEAR_DECAY": _fmt(rates.fear_decay),
        "CONFIG_HOSTAGE_THREAT_SENSITIVITY": _fmt(rates.threat_sensitivity),
        "CONFIG_HOSTAGE_KINDNESS_GAIN": _fmt(rates.kindness_gain),
        "CONFIG_HOSTAGE_GRATITUDE_DECAY": _fmt(rates.gratitude_decay),
        "CONFIG_HOSTAGE_IDENT_GAIN": _fmt(rates.ident_gain),
        "CONFIG_HOSTAGE_FEAR_SUPPRESS": _fmt(rates.fear_suppress),
        "CONFIG_HOSTAGE_THREAT_INITIAL": _fmt(rates.threat_initial),
        "CONFIG_HOSTAGE_THREAT_DECAY": _fmt(rates.threat_decay),
        "CONFIG_HOSTAGE_THREAT_FLOOR": _fmt(rates.threat_floor),
        "CONFIG_HOSTAGE_KINDNESS_SCHEDULE": "; ".join(
            f"day {_fmt(ev.day, 1)} x {_fmt(ev.magnitude, 2)}" for ev in events
        ),
        "CONFIG_GRID_INITIAL_OUTAGE": str(power.get("initial_outage", "3->5")),
        "CONFIG_NEG_DEADLINE_DAYS": _fmt(
            float(negotiation.get("deadline_days", 10.0)), 1
        ),
        "CONFIG_NEG_NEGOTIATOR_DISCOUNT": _fmt(
            float(negotiation.get("negotiator_discount", 0.90))
        ),
        "CONFIG_NEG_CONCESSION_RATE": _fmt(
            float(negotiation.get("concession_rate", 0.08))
        ),
        "CONFIG_NEG_CAPTOR_DISCOUNT_BASE": _fmt(
            float(negotiation.get("captor_discount_base", 0.55))
        ),
        "CONFIG_NEG_CAPTOR_DISCOUNT_GAIN": _fmt(
            float(negotiation.get("captor_discount_gain", 0.45))
        ),
        "CONFIG_NEG_INITIAL_DEMAND": _fmt(
            float(negotiation.get("initial_demand", 0.95))
        ),
        "CONFIG_NEG_INITIAL_OFFER": _fmt(float(negotiation.get("initial_offer", 0.05))),
        "CONFIG_FUSION_STEPS": str(int(fusion.get("steps", 20))),
        "CONFIG_FUSION_MEASUREMENT_NOISE": _fmt(
            float(fusion.get("measurement_noise", 2.0))
        ),
    }
    # The frozen name set is asserted against this dict in
    # tests/test_manuscript_variables.py rather than re-checked here: an
    # in-code guard on a mismatch no input can produce would be unreachable.
    return tokens


def _derived_dataset_tokens(config: dict[str, Any]) -> dict[str, str]:
    """``CONFIG_*`` tokens derived from fixed datasets and module constants.

    These are *not* tunable from ``manuscript/config.yaml``: they are read off
    ``default_pipeline()``, ``default_power_grid()`` and
    ``CHOKE_UTILIZATION_THRESHOLD``. The config only selects *which* dataset
    element to report (the initial outage), never its value.
    """
    # `_config_tokens` runs `_declared_config_tokens` first, which rejects a
    # non-mapping `experiment:` section, so no duplicate guard is needed here.
    experiment = config.get("experiment", {}) or {}
    power = experiment.get("power_grid", {}) or {}
    network = pipeline_security.default_pipeline()
    grid = power_grid.default_power_grid()
    strong_tie = grid.line_id(str(power.get("initial_outage", "3->5")))
    # The "weak tie" is the other interconnector into the strong tie's load-area
    # bus: same target bus, lower rating. Derived from the dataset, never typed.
    weak_ties = sorted(
        (
            line
            for line in grid.lines
            if line.target == strong_tie.target and line.id != strong_tie.id
        ),
        key=lambda line: line.capacity_mw,
    )
    weak_tie = weak_ties[0] if weak_ties else strong_tie
    tokens = {
        "CONFIG_PIPELINE_NODES": str(network.node_count()),
        "CONFIG_PIPELINE_SEGMENTS": str(network.edge_count),
        "CONFIG_CHOKE_UTILIZATION": _fmt(
            pipeline_security.CHOKE_UTILIZATION_THRESHOLD * 100.0, 0
        ),
        "CONFIG_GRID_BUSES": str(grid.n_buses),
        "CONFIG_GRID_LINES": str(len(grid.lines)),
        "CONFIG_GRID_LOAD_MW": _fmt(power_grid.total_load(grid), 0),
        "CONFIG_GRID_STRONG_TIE_MW": _fmt(strong_tie.capacity_mw, 0),
        "CONFIG_GRID_WEAK_TIE": weak_tie.id,
        "CONFIG_GRID_WEAK_TIE_MW": _fmt(weak_tie.capacity_mw, 0),
    }
    return tokens


def resolve_manuscript_tree(
    variables: dict[str, str],
    *,
    manuscript_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    strict: bool = True,
) -> tuple[Path, list[str]]:
    """Copy each manuscript section to ``output/manuscript/``, substituting tokens.

    Only ``NN_*.md`` section files are copied (not sidecars such as
    ``SYNTAX.md``). In strict mode any leftover ``{{TOKEN}}`` fails the
    resolution so the manuscript can never render with raw braces.
    """
    manuscript_dir = (
        Path(manuscript_dir)
        if manuscript_dir is not None
        else PACKAGE_ROOT / "manuscript"
    )
    output_dir = (
        Path(output_dir)
        if output_dir is not None
        else PACKAGE_ROOT / "output" / "manuscript"
    )
    resolved: list[str] = []
    for source in sorted(manuscript_dir.glob("[0-9][0-9]_*.md")):
        text = source.read_text(encoding="utf-8")
        for token, value in variables.items():
            text = text.replace("{{" + token + "}}", value)
        unresolved = sorted(set(_TOKEN_RE.findall(text)))
        if unresolved and strict:
            raise ValueError(
                f"unresolved manuscript tokens in {source.name}: {unresolved}"
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / source.name).write_text(text, encoding="utf-8")
        resolved.append(source.name)
    return output_dir, resolved

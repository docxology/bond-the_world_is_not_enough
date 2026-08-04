"""Manuscript variable hydration for ELEKTRA (the_world_is_not_enough).

Every ``{{TOKEN}}`` in ``manuscript/*.md`` resolves through
:func:`generate_variables`, which reads ``manuscript/config.yaml`` and then
*runs the deterministic domain models* to compute the result tokens. Metrics
are never hand-authored in prose: they flow through this module so the
manuscript cannot drift from the code.

The consuming orchestrator is ``scripts/z_generate_manuscript_variables.py``
(thin wrapper); the live cross-reference gate lives in
``tests/test_manuscript_variables.py``.
"""

from __future__ import annotations

import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import yaml

from the_world_is_not_enough import hostage_psychology, pipeline_security, sub_defense

__all__ = ["generate_variables", "load_manuscript_config", "resolve_manuscript_tree"]

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "manuscript" / "config.yaml"

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
    )

    sensor_count = len(sensors)
    return {
        "RESULT_MAX_FLOW": _fmt(float(analysis["max_flow_kbpd"])),
        "RESULT_MIN_CUT_CAPACITY": _fmt(float(analysis["min_cut_capacity_kbpd"])),
        "RESULT_CHOKE_POINT_COUNT": str(int(analysis["choke_point_count"])),
        "RESULT_TOP_CHOKE_POINT": str(top_choke),
        "RESULT_SENSOR_COVERAGE": _fmt(float(analysis["sensor_coverage"]) * 100.0),
        "RESULT_TAMPER_EVENTS": str(int(tamper["total_events"])),
        "RESULT_TAMPER_DETECTION_RATE": _fmt(float(tamper["detection_rate"]) * 100.0),
        "RESULT_TAMPER_FLOW_LOST": _fmt(float(tamper["flow_lost_kbpd"])),
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
    }


def generate_variables(
    *,
    config_path: str | Path | None = None,
    require_outputs: bool = True,
    now: datetime | None = None,
) -> dict[str, str]:
    """Compute the ``{{TOKEN}}`` → value mapping for the manuscript.

    Args:
        config_path: Override for ``manuscript/config.yaml``.
        require_outputs: When True (default), the domain models must run and
            produce measureable outputs (always satisfied by construction).
        now: Clock override for the generation timestamp (deterministic tests).

    Returns a mapping of every manuscript token to its resolved string value.
    """
    config = load_manuscript_config(config_path)
    paper = config.get("paper", {})
    if not isinstance(paper, dict):
        raise TypeError("manuscript config 'paper' section must be a mapping")

    result_tokens = _run_domain_tokens(config)
    # The result tokens are the strict-mode gate: if the models produced no
    # measurable output (impossible here), fail rather than render N/A.
    if require_outputs and (
        not result_tokens or "RESULT_MAX_FLOW" not in result_tokens
    ):
        raise ValueError(
            "domain models produced no result tokens — cannot hydrate manuscript"
        )

    timestamp = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    return {
        "MISSION_TITLE": str(paper.get("title", "")),
        "MISSION_SUBTITLE": str(paper.get("subtitle", "")),
        "MISSION_FILM": MISSION_FILM,
        "MISSION_CODENAME": MISSION_CODENAME,
        "PACKAGE_VERSION": str(paper.get("version", PACKAGE_VERSION)),
        "PYTHON_VERSION": platform.python_version(),
        "GENERATION_TIMESTAMP": timestamp,
        **_config_tokens(config),
        **result_tokens,
    }


def _config_tokens(config: dict[str, Any]) -> dict[str, str]:
    """Format the deterministic experiment parameters as ``CONFIG_*`` tokens."""
    experiment = config.get("experiment", {}) or {}
    if not isinstance(experiment, dict):
        raise TypeError("manuscript config 'experiment' section must be a mapping")
    pipeline = experiment.get("pipeline", {}) or {}
    submarine = experiment.get("submarine", {}) or {}
    hostage = experiment.get("hostage", {}) or {}
    sensors = submarine.get("sensors", []) or []
    return {
        "CONFIG_SEED": str(experiment.get("seed", 1999)),
        "CONFIG_TAMPER_EVENTS": str(int(pipeline.get("tamper_events", 40))),
        "CONFIG_DETECTION_PROBABILITY": _fmt(
            float(pipeline.get("detection_probability", 0.85))
        ),
        "CONFIG_SUB_GRID": str(int(submarine.get("grid_size", 16))),
        "CONFIG_SUB_SENSORS": str(len(sensors)),
        "CONFIG_HOSTAGE_DAYS": _fmt(float(hostage.get("days", 30.0)), 1),
        "CONFIG_HOSTAGE_DT": _fmt(float(hostage.get("dt", 0.25))),
        "CONFIG_HOSTAGE_ONSET": _fmt(float(hostage.get("onset_threshold", 0.5))),
    }


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

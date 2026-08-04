---
name: the-world-is-not-enough
description: In-repo skill for the ELEKTRA BOND film package (The World Is Not Enough, 1999). Mission codename ELEKTRA.
version: 1.0.0
tags: [bond, film, elektra, pipeline-security, submarine-defense, hostage-psychology]
---

# the-world-is-not-enough (ELEKTRA)

BOND suite film package for *The World Is Not Enough* (1999), mission codename
ELEKTRA. Models three deterministic pillars and adapts them to the frozen
`bond_api` `MissionProvider` protocol.

## When to use

- Building or maintaining `projects/working/bond/the_world_is_not_enough/`.
- Extending the three pillar models or the mission adapter.

## Quick reference

```bash
# Gates
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format src/ scripts/ tests/
uv run mypy src/ scripts/

# Mission + artifacts
uv run python scripts/execute.py                       # outcome + provenance record
uv run python scripts/generate_figures.py              # 3 concept figures
uv run python scripts/z_generate_manuscript_variables.py   # token hydration
```

## Pillars

- `pipeline_security.py` — flow network (17-node Caspian trunk); Edmonds–Karp
  max-flow/min-cut, Brandes betweenness, capacity utilization, tamper sim.
- `sub_defense.py` — passive-sonar equation + normal-CDF detection, risk map,
  Dijkstra least-risk evasion, bearing triangulation.
- `hostage_psychology.py` — four-state Stockholm-syndrome ODE with fixed-step
  RK4 (onset/peak/final + influence ratio).

`mission.py` implements `MissionProvider` (film=`the_world_is_not_enough`,
codename=`ELEKTRA`, seed=`1999`) and registers `GADGETS`. The pure core is
bond-free.

## Pitfalls

- Domain core must not import `bond_api`/`bond_utilities` (layer contract).
- Metrics are tokens — never hand-author numbers in prose.
- Keep `Provenance.wall_time_s = 0.0`; persist with `bond_utilities.mission_io`.
- Sonar params must avoid saturation (ranges/absorption tuned so the risk field
  is not all ~1); see the absorption/threshold values in `manuscript/config.yaml`.
- No literal `{{PLACEHOLDER}}` in numbered manuscript sections (cross-ref gate).

See the package `README.md`, `AGENTS.md`, and `docs/` for full details.

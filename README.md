# the_world_is_not_enough — ELEKTRA

*The World Is Not Enough* (1999) · mission codename **ELEKTRA** · a BOND suite
film package.

Deterministic special-agent mission software modeling six operational pillars
drawn from the film:

1. **Oil-pipeline security graph** — choke points and tamper interdiction.
   Edmonds–Karp max-flow/min-cut, Brandes edge-betweenness, capacity
   utilization, and a deterministic discrete-event tamper simulation.
2. **Nuclear-submarine defense** — evasion and detection. A passive-sonar
   equation with a normal-CDF detection link, least-risk Dijkstra evasion
   routing over the detection field, and bearing-only triangulation.
3. **Stockholm-syndrome influence model** — hostage psychology dynamics. A
   four-state ODE system (fear, gratitude, identification, threat) integrated
   with a fixed-step RK4 scheme that reproduces the onset of the syndrome.
4. **Energy infrastructure** — DC power flow and cascading-failure blackout.
   A linearized load-flow solve and a deterministic outage cascade show how a
   single interconnector cut islands a whole load area.
5. **Hostage negotiation** — Rubinstein alternating-offer bargaining under
   syndrome-driven patience. The syndrome raises the captor's reservation
   value and can push the negotiation to stalemate.
6. **Sensor fusion** — a constant-velocity linear Kalman filter that tracks
   the hijacked submarine from noisy position fixes, cutting position RMSE
   well below the raw-measurement level.

All results are real, deterministic model outputs produced under a single fixed
seed (`1999`); no metric in the manuscript is hand-authored.

## Features

- Pure, infrastructure-free domain core (`src/the_world_is_not_enough/`),
  importable *without* BOND-API.
- A thin `mission.py` adapter implementing the **frozen `bond_api`
  `MissionProvider` protocol** (brief → recon → plan → execute → debrief), with
  domain capabilities registered in a `bond_api` `GadgetRegistry`.
- Thin per-phase CLIs (`scripts/brief.py` … `scripts/debrief.py`) emitting
  canonical BOND-API JSON, plus figure and manuscript-variable scripts.
- Four deterministic concept figures and a token-hydrated manuscript
  (metrics flow through `manuscript_variables.py`, never authored).
- Shared provenance persistence via `bond_utilities.mission_io`.
  `record_provenance_outcome` (deterministic mission epoch).
- ≥90% line+branch coverage on `src/`, zero mocks, ruff + mypy clean.

## Setup

```bash
cd /Users/4d/Documents/GitHub/template/projects/working/bond/the_world_is_not_enough
uv sync --extra dev
```

`bond-api` (Layer 1, frozen protocol) and `bond-utilities` (Layer 0) are
installed as local path dependencies from the same local-only suite tree.

## Usage

```bash
# Mission lifecycle (thin CLIs over the provider)
uv run python scripts/brief.py
uv run python scripts/recon.py
uv run python scripts/plan.py
uv run python scripts/execute.py        # writes output/data/elektra_mission.json
uv run python scripts/debrief.py

# Deterministic figures -> output/figures/
uv run python scripts/generate_figures.py

# Manuscript variable hydration -> output/data + output/manuscript/
uv run python scripts/z_generate_manuscript_variables.py
```

Programmatic mission execution:

```python
from bond_api.discovery import load_provider
provider = load_provider("the_world_is_not_enough", search_paths=["src"])
print(provider.brief())
```

## Package structure

```
src/the_world_is_not_enough/
  pipeline_security.py    # flow network, choke points, tamper sim (pure)
  sub_defense.py          # sonar equation, evasion routing, triangulation (pure)
  hostage_psychology.py   # Stockholm-syndrome ODE model, RK4 (pure)
  power_grid.py           # DC power flow, cascading-failure blackout (pure)
  negotiation_tactics.py  # Rubinstein bargaining + syndrome-driven patience (pure)
  sensor_fusion.py        # linear Kalman tracking of the hijacked sub (pure)
  figures.py              # 4 deterministic concept figures
  manuscript_variables.py # {{TOKEN}} hydration from config + measured outputs
  mission.py              # MissionProvider adapter + gadget registry
scripts/                  # thin per-phase CLIs
tests/                    # zero-mock real-data tests
manuscript/               # token-hydrated manuscript + config.yaml
```

## Testing

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/
uv run mypy src/ scripts/
```

## The BOND suite

This is a film package in the local-only PROJECT BOND suite
(`projects/working/bond/`, 27 film packages + infrastructure). Scope is exactly
this package directory; there is no remote and nothing is pushed. See
`TODO.md` for built modules and declared integration points.

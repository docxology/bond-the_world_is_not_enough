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

The pillars are not six unrelated exercises. The grid model supplies the
sabotage force multiplier behind the pipeline pillar, the bargaining model
consumes the syndrome state produced by the psychology model, and the Kalman
filter re-acquires the hull that the evasion router hid.

All results are real, deterministic model outputs produced under a single fixed
seed (`1999`); no metric in the manuscript is hand-authored.

## Film → software mapping

| In the film | In this package |
| --- | --- |
| Elektra King's Caspian pipeline is targeted for sabotage | `pipeline_security` — where a cut costs the most throughput |
| A single cut cripples the corridor and the city behind it | `power_grid` — the cascade that turns one outage into a regional blackout |
| The nuclear submarine *King William* is hijacked and hides | `sub_defense` — the acoustic field and the least-exposure route through it |
| The hull must be re-found before the weapon is used | `sensor_fusion` — the Kalman track that makes an intercept solvable |
| A captor manipulates a hostage's judgment | `hostage_psychology` — when the emotional bond forms, and how strongly |
| That bond changes what the captor will accept | `negotiation_tactics` — the syndrome moving the reservation value |

## Features

- Pure, infrastructure-free domain core (`src/the_world_is_not_enough/`),
  importable *without* BOND-API.
- A thin `mission.py` adapter implementing the **frozen `bond_api`
  `MissionProvider` protocol** (brief → recon → plan → execute → debrief), with
  domain capabilities registered in a `bond_api` `GadgetRegistry`.
- Thin per-phase CLIs (`scripts/brief.py` … `scripts/debrief.py`) emitting
  canonical BOND-API JSON, plus figure and manuscript-variable scripts.
- Four deterministic concept figures and a token-hydrated manuscript
  (metrics flow through `manuscript_variables.py`, never authored) with a
  strict resolver that refuses to render an unresolved or non-finite token.
- Shared provenance persistence via
  `bond_utilities.mission_io.record_provenance_outcome` (deterministic mission
  epoch).
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

Every module in `src/the_world_is_not_enough/`, one line each:

| Module | Computes |
| --- | --- |
| `pipeline_security.py` | Capacitated flow network of the Caspian trunk: Edmonds–Karp max flow, min-cut recovery, Brandes edge-betweenness, utilization, sensor coverage, and a seeded discrete-event tamper simulation. Pure. |
| `sub_defense.py` | Passive-sonar equation and normal-CDF detection link, the combined risk field, Dijkstra least-exposure evasion routing against a line-of-sight baseline, and bearing triangulation. Pure. |
| `hostage_psychology.py` | Four-state bounded Stockholm-syndrome ODE (fear, gratitude, identification, decaying threat) integrated with fixed-step RK4; onset day, peak, final syndrome, influence ratio. Pure. |
| `power_grid.py` | Linearized DC load flow over a two-area corridor and a deterministic sequential cascading-failure blackout; lost load and blackout fraction. Pure. |
| `negotiation_tactics.py` | Rubinstein alternating-offer equilibrium, the syndrome→captor-patience mapping, and a concession model resolving to settlement, deadline lapse, or stalemate. Pure. |
| `sensor_fusion.py` | Constant-velocity linear Kalman filter over seeded noisy position fixes; RMSE against the raw-measurement baseline, final error, convergence. Pure. |
| `figures.py` | The four deterministic concept figures, rendered headless (`Agg`), no timestamps. |
| `manuscript_variables.py` | `{{TOKEN}}` hydration: reads `manuscript/config.yaml`, runs the models, formats `CONFIG_*` and `RESULT_*` tokens, and refuses blank or non-finite values. |
| `mission.py` | The BOND-API adapter — `MissionProvider` plus the `GADGETS` registry. The only module importing `bond_api`. |

```
scripts/     # thin per-phase CLIs + figure and token generators
tests/       # zero-mock real-data tests, one module per pillar
manuscript/  # token-hydrated manuscript + config.yaml (the experiment block)
docs/        # architecture, testing philosophy, agent instructions
```

## MissionProvider surface

`src/the_world_is_not_enough/mission.py` exposes the **frozen** `bond_api`
protocol. `bond-cli`, the coordinator reconcile, and the orchestrator consume
this shape across every package in the suite, so it does not change:

| Member | Shape |
| --- | --- |
| `MissionProvider.brief()` | → `MissionBrief` (codename `ELEKTRA`, 4 objectives, 6 assets, 3 constraints) |
| `MissionProvider.recon(request)` | → `ReconReport` (goal + one measured finding per pillar) |
| `MissionProvider.plan(brief)` | → `MissionPlan` (8 steps, one or two per pillar) |
| `MissionProvider.execute(plan)` | → `MissionOutcome` (measured results + `Provenance(seed=1999, wall_time_s=0.0, input_hash)`) |
| `MissionProvider.debrief(outcome)` | → `Debrief` (6 lessons derived from the measured outcome) |
| `GADGETS` | module-level `GadgetRegistry` with 8 callables under the film slug |
| `mission_input_hash(plan)` | stable SHA-256 over the canonical plan form |

Depth is added inside the package — more steps, more result keys, more
gadgets — never as a protocol change.

## Testing

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format --check src/ scripts/
uv run mypy src/ scripts/
```

The enforced floor is **90% line + branch on `src/`**, with zero mocks and
zero skips. The achieved figure and live test count are recorded in
[`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md), regenerated from a
real run — this README deliberately does not quote a percentage that would go
stale.

## The BOND suite

This is a film package in the local-only PROJECT BOND suite
(`projects/working/bond/`, 27 film packages + infrastructure). Scope is exactly
this package directory; there is no remote and nothing is pushed. See
`TODO.md` for the open work, the accepted limitations, and the gates.

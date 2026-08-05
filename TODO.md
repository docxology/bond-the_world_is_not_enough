# TODO — the_world_is_not_enough (ELEKTRA)

## Built (phase-2 mission implementation)

### Pure domain core (`src/the_world_is_not_enough/`)
- `pipeline_security.py` — capacitated flow network of the Caspian trunk;
  Edmonds–Karp max-flow/min-cut, Brandes edge-betweenness, capacity
  utilization, sensor coverage, deterministic tamper simulation,
  `analyze_choke_points` report.
- `sub_defense.py` — passive-sonar equation + normal-CDF detection link,
  deterministic risk map, Dijkstra least-risk evasion routing (4-connected,
  self-gauging vs. monotone baseline), bearing triangulation.
- `hostage_psychology.py` — four-state Stockholm-syndrome ODE model
  (fear/gratitude/identification/threat) with fixed-step RK4, onset/peak/final
  syndrome metrics, influence ratio.

### Protocol adapter
- `mission.py` — `ELEKTRA` `MissionProvider` implementing the frozen
  `bond_api` protocol; `Provenance(seed=1999, wall_time_s=0.0, input_hash)`;
  `GADGETS` registered at import (`pipeline_analysis`, `tamper_simulation`,
  `evasion_analysis`, `hostage_dynamics`, `mission_input_hash`).
- `manuscript_variables.py` — `{{TOKEN}}` hydration from
  `manuscript/config.yaml` + measured outputs (config + result token families).
- `figures.py` — three deterministic concept figures.

### Scripts
- `scripts/brief.py`, `recon.py`, `plan.py`, `execute.py`, `debrief.py`,
  `generate_figures.py`, `z_generate_manuscript_variables.py` — thin,
  canonical-JSON emitting phase CLIs. `execute.py` persists provenance via
  `bond_utilities.mission_io.record_provenance_outcome` at a fixed mission
  epoch.

### Tests
- Per-domain (`test_pipeline_security.py`, `test_sub_defense.py`,
  `test_hostage_psychology.py`), adapter (`test_mission.py`), figures,
  manuscript variables (incl. live token cross-reference), script smoke.
  Zero mocks; 148 tests; 97%+ line+branch coverage on `src/`.

## Built (phase-4 deep improvement)

### New pure domain modules (energy infrastructure + hostage engineering)
- `power_grid.py` — energy infrastructure: DC power flow (susceptance-matrix
  solve with slack-connected live component) and a deterministic sequential
  cascading-failure blackout (`cascade_failure`). Canonical two-area corridor:
  cutting the strong `3->5` tie reroutes transfer onto the weak `4->5` tie,
  which trips and islands the whole 220 MW load area (44% blackout).
- `negotiation_tactics.py` — hostage negotiation: Rubinstein alternating-offer
  equilibrium (`equilibrium_shares`), syndrome-driven captor patience
  (`captor_discount_from_syndrome`), and a deterministic concession model
  (`settlement_analysis`) reporting settlement day/split or stalemate/deadline.
  The hostage-psychology syndrome feeds the bargaining layer.
- `sensor_fusion.py` — submarine tracking: constant-velocity linear Kalman
  filter (predict/update, covariance), deterministic seeded measurement
  generation, and RMSE/gain metrics vs. the raw fixes.

### Deepened adapter + wiring
- `mission.py` — protocol surface **unchanged** (frozen `MissionProvider`,
  module-level `GADGETS`); internals deepened to 8 plan steps / richer result
  dict. New gadgets: `power_cascade`, `negotiation_settlement`,
  `submarine_tracking`.
- `manuscript_variables.py` — new `CONFIG_GRID_*`, `CONFIG_NEG_*`,
  `CONFIG_FUSION_*` and `RESULT_BLACKOUT_*`, `RESULT_NEG_*`, `RESULT_TRACK_*`
  tokens; `_config_tokens` extended.
- `figures.py` — fourth figure `sensor_fusion_track.png` (Kalman track vs
  truth vs fixes).

### Tests
- New `test_power_grid.py`, `test_negotiation_tactics.py`,
  `test_sensor_fusion.py`; extended `test_mission.py` (8 steps, new
  result/gadget assertions), `test_figures.py` (4 figures), and
  `test_manuscript_variables.py` (new token values). 230 tests; 97.15%
  line+branch coverage on `src/`.

### Manuscript
- Abstract, methodology (2.4–2.6), results (3.4–3.6 + sensor-fusion figure),
  conclusion, experimental setup, reproducibility, and scope/related-work
  updated with the deepened outputs; `references.bib` extended with Stott
  (1974), Dobson *et al.* (2001), Rubinstein (1982), and Kalman (1960).

## Declared integration points / follow-ups

- **Orchestrator binding.** The package is discoverable by slug
  (`the_world_is_not_enough.mission.MissionProvider`) and registers
  `GADGETS`; a future bond-orchestrator run should consume both via
  `bond_api.discovery` / `GadgetRegistry`. No action needed here.
- **Provenance helper.** Persistence is bound to
  `bond_utilities.mission_io.record_provenance_outcome`; if bond-utilities'
  API changes, re-sync the call in `scripts/execute.py`.
- **Sonar model.** The passive equation is simplified (spherical spreading +
  absorption); a frequency-dependent propagation model is a natural extension.
- **Power-grid model.** The DC cascade is lossless and sequential; a parallel
  (all-overloaded-trip) cascade, reactive/voltage physics, or stochastic
  outage sampling would extend it.
- **Sensor fusion.** The filter fuses noisy position fixes; true
  bearing-only fusion from a maneuvering observer (batch least-squares TMA) is
  a documented follow-up.
- **Hostage model.** Parameters are a modeling assumption exposed in
  `manuscript/config.yaml`; fitting to case data (if datasets become
  available) would replace the by-construction calibration.

## Guardrail status (verified before commit)

- [x] `uv run pytest tests/ --cov=src --cov-fail-under=90` passes
- [x] `ruff check` + `ruff format` clean on `src/ scripts/ tests/`
- [x] `mypy src/ scripts/` clean
- [x] `rg "template[_]code_project"` → zero (bracket-split pattern)
- [x] no mocks (no unittest.mock / MagicMock / @patch)
- [x] `git status` clean after commit

## Verification commands

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format src/ scripts/ tests/
uv run mypy src/ scripts/
rg -n "template[_]code_project" . --glob '!uv.lock' --glob '!.git/**' || echo clean
```

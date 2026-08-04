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

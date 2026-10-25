# TODO — the_world_is_not_enough (ELEKTRA)

ELEKTRA is the *The World Is Not Enough* (1999) film package of the local-only
PROJECT BOND suite: six pure deterministic domain pillars (oil-pipeline
choke-point security, submarine evasion sonar, Stockholm-syndrome ODE dynamics,
DC-power-flow cascading blackout, Rubinstein bargaining under syndrome-driven
patience, Kalman sensor fusion) behind a thin frozen `bond_api.MissionProvider`
adapter, with every manuscript number arriving as a hydrated `{{TOKEN}}`.
Live counts (tests, coverage, tokens, plan steps) are re-measured in
[`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md); the gate numbers are
re-run and recorded in the "Verification" section at the end of this file.
Package surface is in [`README.md`](README.md), module detail in
[`docs/architecture.md`](docs/architecture.md). This file is only what is still
open.

## Round-2 (2026-08-06) — hostile review + single source of truth

This round closed the correctness backlog (C1, C2, V1, V2, V3, V4, D1) and
deepened the manuscript. Measured in this working tree: **405 tests passed, 0
failed, 0 skipped; 100.00% line+branch coverage on `src/`** (gate 90%), ruff
clean, ruff format clean, mypy clean on `src/` + `scripts/`, token gate
resolves 76 variables, and the lineage grep is clean.

### What landed, with test evidence

- **C1 — `mission.py` no longer restates `config.yaml`.** The tunable mission
  inputs now come from one shared builder,
  `manuscript_variables.build_mission_scenario()`, and
  `mission._scenario()` resolves it lazily (no manuscript-tree read at
  import). The mirrored module constants (`_TAMPER_EVENTS`, `_SUB_*`,
  `_HOSTAGE_*`, `_NEGOTIATION`, `_FUSION`, `_GRID_*`) are gone:
  `rg -n "^_(TAMPER|DETECT|SUB|HOSTAGE|GRID|NEGOTIATION|FUSION)"` on
  `mission.py` returns nothing. Evidence: the obsolete mirror test was
  replaced by the completeness guard (V1); full suite green.
- **V1 — config<>adapter completeness guard.** `build_mission_scenario`
  records every config key it consumes (via `_require`); a new test walks the
  `experiment:` block's leaf paths and asserts the builder read them all, so
  an *added* unmapped knob turns the suite red. Evidence:
  `tests/test_mission.py::test_the_scenario_consumes_every_config_leaf`.
- **C2 — config accessors fail closed.** `hostage_params`, `kindness_events`,
  `hostage_initial_state` and the scenario builder raise `KeyError` on a
  missing *required* key instead of silently defaulting. Evidence: the old
  "falls back to defaults" test was replaced by per-rate / per-block
  negative controls (`tests/test_manuscript_variables.py::TestHostageParametersAreReallyConfigured`)
  and a malformed-section sweep (`TestSharedScenarioBuilder`), plus a
  manual check: deleting any rate from `config.yaml` makes the generator exit
  non-zero.
- **V2 — residual uncovered branches closed; 100% coverage.** The five listed
  branches were either covered with real inputs or deleted as provably
  unreachable: the pipeline min-cut DFS revisit (diamond with a downstream
  bottleneck) and dead `edge_flow` guard (removed), the power-grid
  `if not active` + `max_steps` exits (two new cascade tests), the figure BFS
  depth false-arm (a diamond-network figure test), and the `sub_defense`
  Dijkstra `visited` skip (removed — provably unreachable given uniform
  per-cell entry cost + strict `<` + min-heap).
- **V3 — COUNTS staleness gate.** `tests/test_counts_staleness.py` re-derives
  every structural row of COUNTS.md (steps 8, result keys 29, gadgets 8,
  tokens 76, sections 9, figures 4, stages 5, lessons 6) from live objects.
- **V4 — mock/lineage rules are now tests.** `tests/test_guardrails.py` walks
  `src/`, `scripts/`, `tests/` and fails on mock-framework patterns or the
  bracket-split lineage string, with positive controls.
- **D1 — `manuscript_variables.__all__`** now exports the three documented
  config->model helpers (`hostage_params`, `kindness_events`,
  `hostage_initial_state`) plus `build_mission_scenario`, `MISSION_CODENAME`,
  `MISSION_FILM`, and `docs/architecture.md` names the same surface.
- **Manuscript.** Added Table 3 (headline measured results, all live
  `RESULT_*` tokens) in §3; §6 gained a "Verification gates" subsection
  describing the single-source-of-truth, fail-closed, coverage, mock/lineage
  and COUNTS guards; §7's Stockholm paragraph now states the fail-closed
  config contract.
- **docs/architecture.md** updated: the paragraph describing the old mirrored
  constants now documents `_scenario()` + `build_mission_scenario()`; the
  manuscript-variables section documents the fail-closed accessors.

### Gate numbers (this working tree, re-measured)

| Command | Result |
|---|---|
| `uv run pytest tests/ --cov=src --cov-fail-under=90` | 405 passed, 0 failed, 0 skipped; 100.00% (floor 90%) |
| `uv run ruff check src/ scripts/ tests/` | All checks passed |
| `uv run ruff format --check src/ scripts/ tests/` | clean |
| `uv run mypy src/ scripts/` | Success: no issues in 17 source files |
| `z_generate_manuscript_variables.py` | Resolved 76 variables, exit 0 |
| lineage grep | clean |

### Left for a future round

- The extension backlog (E1–E5) is unchanged and still open: delivered-volume
  tamper accounting, frequency-dependent sonar propagation, parallel cascade
  tripping, bearing-only target-motion analysis, and asymmetric-information
  bargaining. None is a defect.
- The known limitations section is unchanged and still accurate.

## Open work

All correctness (C1, C2), verification (V1–V4) and documentation (D1) items
that used to live here are **closed** — see "Round-2 (2026-08-06)" above for
what landed, the test that binds each one, and the re-measured gate numbers.
The items below are the ones genuinely still open.

### Extension

Genuine future work; none of these is a defect.

**E1 — delivered-volume tamper model.** `simulate_tamper`
(`src/the_world_is_not_enough/pipeline_security.py:448`) charges every
undetected event `edge.capacity * nominal_downtime_days`, i.e. the segment's
*rated* capacity, regardless of what the max-flow solution actually routes
through it — so tampering a dead-end spur is priced above its marginal delivery
impact and the reported total is an upper bound. A truer model re-solves the
max flow with the damaged segment removed and charges the *delivery shortfall*.
*Done looks like:* an opt-in `accounting="delivered"` mode reporting a shortfall
volume alongside the rated-capacity upper bound, both tokenised, and the
upper-bound caveat in `07_scope_and_related_work.md:26-30` narrowed to the mode
it describes.
*Demonstrate:* new tests assert the delivered-shortfall total is ≤ the
rated-capacity total on the canonical dataset and strictly smaller when a spur
is tampered; then
`uv run python scripts/z_generate_manuscript_variables.py`. (Directly from the
unresolved-findings file.)

**E2 — frequency-dependent sonar propagation.** `passive_sonar_snr`
(`src/the_world_is_not_enough/sub_defense.py`) uses spherical spreading plus a
single `absorption_db_per_km`. A frequency-banded transmission-loss model
(Thorp absorption, or a bottom-bounce term) changes the shape of the risk field
and therefore the routed evasion path. Needs a new `Sensor` field, a config key,
and a scope-section update.
*Demonstrate:* a test showing two frequency bands produce different routes on
the same geometry, plus a regenerated §3 token set.

**E3 — parallel cascade tripping.** `cascade_failure`
(`src/the_world_is_not_enough/power_grid.py:261`) trips only the single
most-overloaded line per step. Real cascades trip every overloaded line in a
time step; the sequential rule is why the reported blackout is documented as a
conservative lower bound.
*Done looks like:* a `mode="parallel"` option reporting both magnitudes, and
the "parallel-time-step tripping" clause removed from
`07_scope_and_related_work.md`.

**E4 — bearing-only target-motion analysis.** `sensor_fusion` fuses noisy
*position* fixes because bearing-only tracking from a stationary observer is
scale-ambiguous. Batch least-squares TMA from a manoeuvring observer would match
the film's geometry more honestly. Largest of the four.

**E5 — asymmetric-information bargaining.** `negotiation_tactics` assumes both
parties know both discount factors. A one-sided-uncertainty variant would turn
the stalemate threshold from a point into a distribution.

## Known limitations (not bugs)

Recorded so a future pass does not re-litigate them.

- **Hostage rate constants are chosen, not estimated.** All nine live in
  `manuscript/config.yaml` under `experiment.hostage.dynamics` and each is
  perturbed by a test that asserts the syndrome index moves, so the exposure is
  consumption rather than naming. But there is no independent ground truth for
  the syndrome trajectory: the reported onset day, peak and final index are
  properties *of this parameterisation* and carry no uncertainty interval.
  Stated in `manuscript/07_scope_and_related_work.md`. Fitting to case data is
  out of scope for this package.
- **The *form* of the ODE system is hardcoded.** `hostage_psychology.derivatives`
  is not tunable from config; only the rates, the initial state and the kindness
  schedule are. §7 says so.
- **The syndrome→patience map is a declared assumption.**
  `captor_discount_from_syndrome` is `clamp(base + gain * S)`, linear by
  declaration, not fitted. It is the only cross-pillar data dependency in the
  package, so it carries real weight in §3.5 and must stay labelled as an
  assumption until bargaining-under-duress data exists.
- **Tamper loss is an upper bound in kbbl.** Accepted while E1 is open; the
  rated-vs-carried distinction and the volume-vs-rate unit are stated in
  `manuscript/03_results.md` and `07_scope_and_related_work.md`, and
  `RESULT_TOKEN_UNITS` makes re-labelling it `kbbl/day` fail hydration.
- **Blackout magnitude is a conservative lower bound** (sequential cascade,
  see E3) and the trip *sequence* is one deterministic path, not a distribution.
- **Sensor fusion consumes position fixes, not true bearings** (scale ambiguity,
  see E4).
- **Three datasets are not config-tunable by design:**
  `pipeline_security.default_pipeline()`, `power_grid.default_power_grid()`, and
  `pipeline_security.CHOKE_UTILIZATION_THRESHOLD`. `manuscript/05_experimental_setup.md`
  marks their nine Table-1 rows `derived`, and the split is enforced in code via
  `DECLARED_CONFIG_TOKENS` / `DERIVED_DATASET_TOKENS`.
- **The `bond_api.MissionProvider` protocol is frozen.** Depth is added inside
  the package (more plan steps, result keys, gadgets), never as a protocol
  change. `mission.py` stays the only module importing `bond_api`; the domain
  core must remain importable without it.
- **Local-only suite.** The suite tree is local-only; this package's only
  remote is its GitHub publish mirror (`origin`), and commits are path-scoped
  inside this repo.

## Verification

All five must pass before a commit lands. Run from the package root.

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format --check src/ scripts/ tests/
uv run mypy src/ scripts/
uv run python scripts/z_generate_manuscript_variables.py   # strict token gate
rg -n "template[_]code_project" . --glob '!uv.lock' --glob '!.git/**' || echo clean
```

Expected outcomes, re-measured 2026-10-25:

| Command | Expected |
| --- | --- |
| `pytest … --cov-fail-under=90` | `405 passed`, `Total coverage: 100.00%` (floor 90%) |
| `ruff check` / `ruff format --check` | `All checks passed!` / `41 files already formatted` |
| `mypy src/ scripts/` | `Success: no issues found in 17 source files` |
| `z_generate_manuscript_variables.py` | `Resolved 76 manuscript variables -> output/data/manuscript_variables.json`, exit 0 |
| lineage grep | `clean` |
| `git status --short` | empty after commit |

If `uv` reports `Failed to initialize cache at ~/.cache/uv` that is a sandbox
restriction, not a package failure — re-run the same command with the sandbox
disabled. Re-measure rather than quoting: the headline numbers above and in
`docs/_generated/COUNTS.md` are only valid until the next change.

# TODO — the_world_is_not_enough (ELEKTRA)

ELEKTRA is the *The World Is Not Enough* (1999) film package of the local-only
PROJECT BOND suite: six pure deterministic domain pillars (oil-pipeline
choke-point security, submarine evasion sonar, Stockholm-syndrome ODE dynamics,
DC-power-flow cascading blackout, Rubinstein bargaining under syndrome-driven
patience, Kalman sensor fusion) behind a thin frozen `bond_api.MissionProvider`
adapter, with every manuscript number arriving as a hydrated `{{TOKEN}}`.
Measured on 2026-08-05 in this working tree: **362 tests passed, 0 failed, 0
skipped; 99.38% line+branch coverage on `src/`** (gate 90%), ruff clean, ruff
format clean, mypy clean on `src/` + `scripts/`, and the strict token gate
resolves 76 variables. Package surface is in [`README.md`](README.md), module
detail in [`docs/architecture.md`](docs/architecture.md), counts in
[`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md). This file is only
what is still open.

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

### Correctness

**C1 — `mission.py` restates `config.yaml` instead of reading it.**
The experiment parameters are declared twice: in
`manuscript/config.yaml` under `experiment:` (read by
`manuscript_variables.load_manuscript_config`) and again as module constants in
`src/the_world_is_not_enough/mission.py:71-148` (`_TAMPER_EVENTS`,
`_DETECT_PROB`, `_SUB_*`, `_HOSTAGE_*`, `_GRID_*`, `_NEGOTIATION`, `_FUSION`).
The two are today kept equal by a test
(`tests/test_mission.py:121-178`), so "the mission and the manuscript measure
the same run" (`docs/architecture.md:210`) is a *checked guarantee*, not a
single source of truth — a maintainer can still edit one side and only learn
about it from a red suite.
*Done looks like:* `mission.py` derives its parameters from the config block
(or from one shared builder), the mirrored constants are gone, and
`test_every_mirrored_constant_equals_its_config_key` is deleted as obsolete
rather than kept as a crutch — without `mission.py` gaining a hard dependency
on the manuscript tree at import time (the domain core must stay importable
without `bond_api` and without `manuscript/`).
*Demonstrate:* `rg -n "^_(TAMPER|DETECT|SUB|HOSTAGE|GRID|NEGOTIATION|FUSION)"
src/the_world_is_not_enough/mission.py` returns nothing, and
`uv run pytest tests/ --cov=src --cov-fail-under=90` is still green.
(From the unresolved-findings file: "mission.py still restates the experiment
block instead of reading it.")

**C2 — config accessors fail open: a deleted key is silently defaulted.**
`src/the_world_is_not_enough/manuscript_variables.py:176` builds
`DynamicsParams` with `rates.get(name, getattr(default, name))`; lines
`196-198` and `213-215` return `hostage_psychology.DEFAULT_KINDNESS_EVENTS` /
`DEFAULT_INITIAL_STATE` when the config key is absent; line 225 uses
`config.get("experiment", {}) or {}`. Because the module defaults are
numerically identical to the config values, **deleting**
`experiment.hostage.dynamics.fear_decay` (or the whole `hostage:` block)
changes no output and no test goes red — yet
`manuscript/07_scope_and_related_work.md` (last paragraph) claims all nine rate
constants, the initial state and the kindness schedule "are typed in
`manuscript/config.yaml` … and consumed by the model". The perturbation tests
in `tests/test_manuscript_variables.py` only bind values that are *present*.
*Done looks like:* the accessors raise on a missing required key (fail closed),
and a test deletes each of the nine rates, the `initial_state`, the
`kindness_events` list and the `experiment` block in a temp-copied config and
asserts a raise.
*Demonstrate:* `uv run pytest tests/test_manuscript_variables.py -k missing -v`
passes, and manually deleting `fear_decay` from `manuscript/config.yaml` then
running `uv run python scripts/z_generate_manuscript_variables.py` exits
non-zero (restore the file afterwards).

### Verification

**V1 — the config↔adapter mirror test is an enumerated allow-list.**
`tests/test_mission.py:121-178` asserts a hand-written pair for each mirrored
value. It catches a *changed* value on either side, but a config key added to
`experiment:` with no counterpart in `mission.py` (or a `mission.py` constant
that no longer maps to any key) is not detected — the gate has no completeness
half. This is the same failure mode the test's own docstring was written to
close.
*Done looks like:* the test is driven by a declared key→constant map that is
also asserted to cover every leaf of the `experiment:` block, so adding an
unmapped config key turns the suite red.
*Demonstrate:* add `experiment.pipeline.unused_probe: 1` to
`manuscript/config.yaml`, run `uv run pytest tests/test_mission.py -q`, and see
it fail; remove the key and see it pass. Superseded automatically if C1 lands.

**V2 — six residual uncovered branches (4 uncovered statements).**
From the run above (`--cov-report=term-missing`), each is a defensive arm the
fixed datasets never take. Decide per branch: cover it with a real input, or
delete it as unreachable given the dataclass validation.
| Location | Branch |
| --- | --- |
| `src/the_world_is_not_enough/pipeline_security.py:284-285` | `if node in reachable: continue` in the min-cut reachability DFS |
| `src/the_world_is_not_enough/pipeline_security.py:344-345` | `if not edge_flow: return {}` in the Brandes edge-betweenness tail |
| `src/the_world_is_not_enough/power_grid.py:290-291` (+ partial `289->310`) | `if not active: break`, and the `max_steps`-exhausted loop exit |
| `src/the_world_is_not_enough/sub_defense.py:219-220` | `if node in visited: continue` in the Dijkstra evasion loop |
| `src/the_world_is_not_enough/figures.py:78->77` | the false arm of `if nxt not in depth` in the BFS depth layout |
*Done looks like:* the `Missing` column is empty for all five modules, either
because a test drives the branch or because the branch no longer exists.
*Demonstrate:* `uv run pytest tests/ --cov=src --cov-report=term-missing -q |
rg "pipeline_security|power_grid|sub_defense|figures"` shows `100.00%` and no
missing lines. (Recorded as out-of-scope in the unresolved-findings file:
"Four residual uncovered branches remain outside my findings' scope".)

**V3 — `docs/_generated/COUNTS.md` has no staleness gate.**
Every number in that file (362 tests, 99.38%, 76 tokens, 8 plan steps, 29
result keys, 8 gadgets, 4 figures) is hand-copied from a run. Nothing
re-measures them: `rg -l COUNTS tests/ scripts/` returns nothing. The table can
drift silently the moment a test is added, which is exactly the failure the
file's own header warns about.
*Done looks like:* a test re-derives the structural rows (plan steps, result
keys, gadgets, generated tokens, figure count, domain/support module counts)
from live objects and asserts they equal the values parsed out of
`docs/_generated/COUNTS.md`; the two run-dependent rows (test count, coverage)
stay documented as regenerated by command.
*Demonstrate:* edit any structural number in `COUNTS.md`, run
`uv run pytest tests/ -q`, see it fail; revert and see it pass.

**V4 — the "zero mocks" and "no `template[_]code[_]project` lineage" rules are
manual greps, not tests.** `AGENTS.md` lists both as hard rules and the
verification block runs them by hand; nothing in `tests/` enforces either.
Verified this session that both are currently *true*
(`rg -n "unittest.mock|MagicMock|mocker\.|monkeypatch\b" tests/*.py` → no
matches; the lineage grep → clean), so this is a missing guard, not a live
violation.
*Done looks like:* a test in `tests/` walks `tests/*.py` and `src/`+`scripts/`
and asserts zero matches for the mock-framework patterns and the bracket-split
lineage string, with a positive control proving the matcher fires on a planted
string.
*Demonstrate:* `uv run pytest tests/ -k "no_mocks or lineage" -v` passes and
fails when a `from unittest import mock` line is temporarily added to a test
file.

### Documentation

**D1 — `manuscript_variables.__all__` omits three documented public helpers.**
`src/the_world_is_not_enough/manuscript_variables.py:34-41` exports six names.
`docs/architecture.md:236` documents `hostage_params()`, `kindness_events()`
and `hostage_initial_state()` as the public config→model builders, and
`tests/test_mission.py:157-159` imports them as such. Either they belong in
`__all__` or the doc should mark them internal.
*Done looks like:* `__all__` and `docs/architecture.md` name the same public
surface for that module.
*Demonstrate:* `uv run python -c "import sys; sys.path.insert(0,'src'); from
the_world_is_not_enough import manuscript_variables as MV;
print(sorted(MV.__all__))"` lists the three helpers, and
`rg -n "hostage_params|kindness_events|hostage_initial_state"
docs/architecture.md` agrees.

Nothing else open here. Checked this session: the six adversarial-audit
findings in `output/verify/the_world_is_not_enough.json` are all reflected in
the current text — the §5/§7 config-exposure claim now matches
`manuscript/config.yaml` (all nine rates present), the tamper number is typed
as a cumulative volume in kbbl with the upper-bound caveat in
`manuscript/03_results.md:29-40` and `07_scope_and_related_work.md:26-30`,
`RESULT_NEG_CAPTOR_LEVERAGE_PCT` is rendered as a labelled percent relative
increase, `manuscript/05_experimental_setup.md` distinguishes `config.yaml`
rows from `derived` rows, `tests/test_claim_ledger.py:98-137` runs a real
mutation control with a positive control, and `docs/architecture.md:90-113`
documents the `hostage_psychology` dataclasses.

### Extension

Genuine future work; none of these is a defect.

**E1 — delivered-volume tamper model.** `simulate_tamper`
(`src/the_world_is_not_enough/pipeline_security.py:487-511`) charges every
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
(`src/the_world_is_not_enough/power_grid.py:289-308`) trips only the single
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
- **Local-only.** No remote, nothing is pushed; commits are path-scoped inside
  this package repo.

## Verification

All five must pass before a commit lands. Run from the package root.

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format --check src/ scripts/ tests/
uv run mypy src/ scripts/
uv run python scripts/z_generate_manuscript_variables.py   # strict token gate
rg -n "template[_]code_project" . --glob '!uv.lock' --glob '!.git/**' || echo clean
```

Expected outcomes, as measured 2026-08-05:

| Command | Expected |
| --- | --- |
| `pytest … --cov-fail-under=90` | `352 passed`, `Total coverage: 99.38%` (floor 90%) |
| `ruff check` / `ruff format --check` | `All checks passed!` / `39 files already formatted` |
| `mypy src/ scripts/` | `Success: no issues found in 17 source files` |
| `z_generate_manuscript_variables.py` | `Resolved 76 manuscript variables -> output/data/manuscript_variables.json`, exit 0 |
| lineage grep | `clean` |
| `git status --short` | empty after commit |

If `uv` reports `Failed to initialize cache at ~/.cache/uv` that is a sandbox
restriction, not a package failure — re-run the same command with the sandbox
disabled. Re-measure rather than quoting: the headline numbers above and in
`docs/_generated/COUNTS.md` are only valid until the next change.

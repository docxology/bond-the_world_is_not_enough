# Testing Philosophy — the_world_is_not_enough (ELEKTRA)

Zero mocks. Every test exercises the real algorithms, models, and CLIs with
real deterministic inputs.

## Core tenets

### Real data and real computation only

No `MagicMock`, `mocker.patch`, `unittest.mock`, `create_autospec`, or
`monkeypatch` on a dependency. There is nothing to fake: the six domain
modules are pure functions over declared datasets, and `bond_api` /
`bond_utilities` are real local path dependencies that install and run. HTTP,
databases, and the network do not appear anywhere in this package, so the
usual reasons to reach for a mock do not arise.

Where a test needs a *different* scenario it builds a real one — a
hand-constructed `PipelineNetwork`, a small `PowerGrid` whose load flow can be
solved by hand, a uniform risk field with a known optimum.

### Assertions must bind truth, not shape

A test that asserts a dict has a key, or that a float is a float, passes
whatever the code does. The assertions here pin values that would change if
the mathematics were wrong:

- **Analytic identities.** Max flow equals min-cut capacity (the max-flow /
  min-cut theorem). `Phi(0) = 0.5`, `Phi(1.96) ≈ 0.975`. RK4 integration of
  exponential decay matches the closed form. Dijkstra over a uniform field
  costs exactly the Manhattan distance times the cell risk. The threat
  schedule matches `floor + initial * exp(-decay * t)` to `1e-12`.
- **Closed-form model outputs.** The Rubinstein equilibrium share is checked
  against `(1 - d_n)/(1 - d_c d_n)`; each settlement branch is checked against
  the crossing time its own algebra predicts.
- **Derived-not-typed invariants.** `CONFIG_PIPELINE_NODES` is asserted equal
  to `default_pipeline().node_count()`, not to the literal `17`, so the token
  cannot drift from the dataset.
- **Cross-consistency.** The choke-point set is asserted to be exactly the set
  of segments at or above `CHOKE_UTILIZATION_THRESHOLD` — checked against the
  constant, so an inlined literal in the rule would fail the test.

### Every gate must be able to fail

A guard, threshold, or validation that no input can trip is not a gate — it is
decoration that reads as safety. Two concrete cases in this package:

- `manuscript_variables._assert_measurable` originally checked only that a key
  it had itself just written was present. It now rejects blank and non-finite
  values and is tested by corrupting one entry of the **real** token map, so
  the test proves the gate rejects exactly what the manuscript would otherwise
  render.
- `dijkstra_evasion`'s "no path exists" guard is exercised with an
  infinite-cost wall through the lattice — **with a positive control** that
  the same field without the wall routes successfully, so the failure is
  attributable to the wall and not to a broken test.

- `data/claim_ledger.yaml` registered nine headline numbers and was read by
  nothing, while its own header called the claims auditable.
  `test_claim_ledger.py` now asserts each recorded value equals the live value
  of the token it cites — and asserts the ledger is non-empty first, so a
  deleted claims list cannot make the parametrized suite pass vacuously.
  Its falsifiability control used to be
  `assert str(claim['value']) + '9' != variables[token]`, which is true for
  every string under every implementation and therefore demonstrated nothing.
  It has been replaced: the comparison itself lives in `stale_claims()`, the
  parametrized suite routes through it, and `TestLedgerCanFail` runs it over a
  corrupted copy of the **real** ledger — once per claim, plus an
  unknown-token case and an all-drifted case — with the uncorrupted ledger as
  the positive control. Breaking `stale_claims` turns the class red.

- `manuscript_variables._assert_units_consistent` is the unit gate added after
  the tamper simulation reported a cumulative volume of 9660 under a
  `kbbl/day` label — 23x the corridor's own max flow. It requires every
  `RESULT_*` token to declare a unit in `RESULT_TOKEN_UNITS` and requires any
  token declared a *rate* to sit below the physical ceiling of the system it
  describes. Re-labelling the tamper volume `kbbl/day` makes hydration fail.

- The manuscript's §5 "Source" column claims which rows come from
  `config.yaml` and which are read off a fixed dataset. That is checked
  against `DECLARED_CONFIG_TOKENS` / `DERIVED_DATASET_TOKENS` by parsing the
  section, so a mislabelled row fails the suite. Naming a knob in a config
  file is not evidence it is consumed, so each of the nine hostage rate
  constants (plus the kindness schedule, the initial state, and the four
  bargaining knobs) is *perturbed* in a temporary config and the reported
  result is asserted to move.

When a branch genuinely cannot be reached, the right answer is to delete it,
not to write a test that pretends. That is why the "slack bus islanded" branch
in `dc_power_flow` was removed rather than covered.

### Determinism is tested, not assumed

Two runs with the same seed must produce identical outputs.
`test_mission.py::TestExecute::test_deterministic` compares full outcomes
*including the `input_hash`*, and each domain module has its own determinism
test. Provenance carries `wall_time_s = 0.0`, so no test ever asserts on a
clock.

### Error branches are covered

Dataclass validation and input bounds (`ValueError` / `TypeError`) are
asserted for every public entry point, including the ones no happy path
reaches: blank network source/sink, non-`PipelineEdge` insertion, negative
sensor levels, a negative discount gain, and a non-mapping `experiment:`
section.

### Subprocess smoke, not import smoke

The phase CLIs are executed as real subprocesses (`sys.executable`,
`cwd=root`) so the tests prove they load, run, emit canonical JSON, and write
their artifacts — an import-only test would not catch a broken `sys.path`
bootstrap or a bad argparse wiring.

## Coverage

The enforced gate is **≥90% line + branch on `src/`**:

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
```

The measured achievement and live test count are recorded in
[`_generated/COUNTS.md`](_generated/COUNTS.md); regenerate that file from a
real run rather than quoting a percentage in prose here.

## Test layout

| File | Exercises |
| --- | --- |
| `test_pipeline_security.py` | flow network validation, Edmonds–Karp max-flow, min-cut recovery, Brandes betweenness, utilization, sensor coverage, risk normalization, choke-threshold consistency, tamper simulation |
| `test_sub_defense.py` | passive-sonar equation, normal CDF, detection probability, risk-map construction, Dijkstra evasion (incl. the unreachable-goal guard with a positive control), line-of-sight baseline, bearing triangulation |
| `test_hostage_psychology.py` | four-state ODE, RK4 accuracy, state bounds, threat schedule against its closed form, onset regimes, determinism |
| `test_power_grid.py` | line/grid validation, susceptance solve, DC load flow on hand-built grids, connectivity, cascade tripping order, blackout accounting |
| `test_negotiation_tactics.py` | parameter validation, Rubinstein equilibrium, syndrome→patience mapping, all three settlement outcomes (stalemate, deadline, settled) and both floor-binding branches |
| `test_sensor_fusion.py` | track generation determinism, Kalman predict/update, RMSE and gain against the raw-measurement baseline, convergence |
| `test_mission.py` | protocol conformance, all five stages, eight plan steps, provenance and `input_hash` determinism, gadget registration, discovery, serialization |
| `test_figures.py` | deterministic generation of all four figures (headless `Agg`) |
| `test_manuscript_variables.py` | config loading and validation, token hydration, derived-dataset tokens, the measurability gate, the unit gate and rate ceilings, tamper-volume accounting, the leverage token's relative-vs-absolute reading, config-knob *consumption* for every hostage rate and bargaining knob, the §5 Source-column partition, example-config sync, the architecture-doc public-surface gate, strict/non-strict tree resolution, and the live cross-reference that every `{{TOKEN}}` in a numbered section is generated |
| `test_claim_ledger.py` | binds every entry of `data/claim_ledger.yaml` to the live value of the token it cites, plus a non-empty check and a per-claim mutation control on the comparison function itself |
| `test_scripts_smoke.py` | the phase CLIs and artifact scripts as real subprocesses |

## Deterministic-input guidance

- Prefer fixed inputs. Where a random *field* is convenient in a test, build it
  with `np.random.default_rng(seed)` so it is reproducible.
- Never assert on wall-clock; provenance reports `wall_time_s = 0.0` and the
  generation timestamp accepts a `now=` override.
- When asserting a measured value, prefer deriving the expectation from the
  model object (`default_pipeline().edge_count`) over pasting the number, so
  changing the dataset fails loudly in one place instead of drifting silently.

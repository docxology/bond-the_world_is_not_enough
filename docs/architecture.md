# Architecture — the_world_is_not_enough (ELEKTRA)

This document describes the package as it actually is: what each module in
`src/the_world_is_not_enough/` computes, how the pieces compose, and how
`mission.py` implements the frozen `bond_api` `MissionProvider`.

## Layer boundaries

```
scripts/                          # thin orchestrators (argv shaping + print)
   |  // may import bond_api, bond_utilities, and src/
   v
src/the_world_is_not_enough/
   mission.py                     # ADAPTER: bond_api MissionProvider + GADGETS
   manuscript_variables.py        # token hydration (config + measured outputs)
   figures.py                     # four deterministic figures (Agg)
   |  // all of the below are pure, bond-free, deterministic
   v
   pipeline_security.py  sub_defense.py          hostage_psychology.py
   power_grid.py         negotiation_tactics.py  sensor_fusion.py
```

Only `mission.py` imports `bond_api`. The six domain modules import stdlib plus
numpy only, so the mathematics still runs if the protocol dependency is
unavailable — that is the layer-contract guarantee, and `tests/test_mission.py`
exercises the adapter separately from the cores.

## The six pure domain modules

Each module owns one pillar. None of them import each other; composition
happens one layer up, in `mission.py` and `manuscript_variables.py`.

### `pipeline_security.py` — flow network, choke points, tamper

The Caspian crude corridor as a capacitated directed graph.

- `PipelineEdge` / `PipelineNetwork` — validated dataclasses; the network
  indexes edges by `source->target` id and rejects duplicates and self-loops.
- `default_pipeline()` — the canonical dataset: a mainline from `PUMP0` to
  `TERM` plus junction spurs, with `J4->J5` deliberately under-capacity.
- `edmonds_karp()` — max flow by shortest augmenting path over the residual
  network.
- `min_cut_edges()` — the minimum s-t cut, recovered as the edges leaving the
  source-reachable set of the final residual graph. Its capacity equals the
  max flow (the max-flow/min-cut theorem, asserted in the tests).
- `edge_betweenness()` — Brandes edge-betweenness centrality: the topological
  (rather than capacity) view of structural importance.
- `flow_criticality()` / `edge_utilization()` — which segments carry the flow,
  and at what fraction of their rating.
- `analyze_choke_points()` — the combined report. A *choke point* is a
  load-bearing segment at or above `CHOKE_UTILIZATION_THRESHOLD` (0.9) of
  rated capacity.
- `simulate_tamper()` — a deterministic discrete-event simulation: attempts
  choose a segment weighted by declared risk (`random.Random(seed)`), guarded
  segments interdict with a per-sensor probability, and undetected events are
  charged their segment's rated capacity for `nominal_downtime_days`. The
  reported `throughput_lost_kbbl` is therefore a cumulative **volume**, not a
  per-day rate, and is not comparable against the max flow — it may exceed it.
  It is also an upper bound: a segment is charged its full rating even where
  the max-flow solution routes less through it.
- `sensor_coverage()`, `normalize_risk_profile()`, `network_fingerprint()` —
  coverage fraction, risk prioritisation, and a stable topology hash.

### `sub_defense.py` — sonar detection and evasion routing

- `Sensor` — a validated passive listening post (source level, noise level,
  absorption, detection threshold).
- `passive_sonar_snr()` — the passive sonar equation
  `SNR = SL - TL(r) - NL + DI` with spherical spreading plus absorption.
- `normal_cdf()` / `detection_probability()` — the operator performance curve
  `Phi((SNR - DT)/sigma)`.
- `build_risk_map()` — combines sensors by the independent rule
  `R = 1 - prod(1 - P_d,i)` across a square grid, producing the field the
  submarine must minimise exposure over. No random draws.
- `dijkstra_evasion()` — least-cumulative-exposure path on the 4-connected
  lattice, with an insertion counter breaking cost ties deterministically.
- `straight_line_path()` — the monotone line-of-sight baseline route, and
  `evasion_analysis()` — routed exposure against that baseline in the *same*
  search space, so the routed path is provably no worse.
- `triangulate_bearings()` — least-squares intersection of two passive
  bearings to localise an emitter.
- `scenario_fingerprint()` — a stable hash of the sensor mosaic and grid.

### `hostage_psychology.py` — Stockholm-syndrome dynamics

A four-state bounded ODE system: fear `F`, gratitude `G`, identification `I`,
and a decaying threat input `T(t)`, with a Gaussian-smoothed kindness impulse
train driving gratitude.

- `DynamicsParams` — the validated frozen dataclass holding the nine rate
  constants (`fear_decay`, `threat_sensitivity`, `kindness_gain`,
  `gratitude_decay`, `ident_gain`, `fear_suppress`, `threat_initial`,
  `threat_decay`, `threat_floor`); every one is non-negative or construction
  fails. These are the model's declared assumption, typed in
  `manuscript/config.yaml` under `experiment.hostage.dynamics` and read by
  `manuscript_variables.hostage_params()`.
- `KindnessEvent` — a validated `(day, magnitude)` small-kindness act;
  `DEFAULT_KINDNESS_EVENTS` and `DEFAULT_INITIAL_STATE` are the canonical
  schedule and starting state, mirrored in the config file.
- `threat_schedule()` — the decaying captivity-threat input
  `floor + T0 * exp(-lambda t)`.
- `derivatives()` — the ODE right-hand side `(dF/dt, dG/dt, dI/dt)`, and
  `rk4_step()` — one classical fixed-step Runge–Kutta advance of it. The
  *form* of these equations is fixed in code and is not configurable.
- `syndrome_index()` — the composite `S = clamp((2I + G - F)/3)`.
- `integrate_dynamics()` — fixed-step classical RK4 over the horizon. The
  saturating `(1 - x)` terms keep every state inside `[0, 1]`.
- `HostageDynamicsResult` — the full result: the four time series plus the
  reported onset day (first crossing of the threshold), peak, peak day, final
  value, and influence ratio, with `as_dict()` for the JSON summary.

This module is phenomenological decision support, not a clinical instrument;
`manuscript/07_scope_and_related_work.md` states that limit.

### `power_grid.py` — DC power flow and cascading blackout

- `GridLine` / `PowerGrid` — validated buses, lines and net nodal injections
  (which must sum to zero); `with_lines()` produces the restricted grid the
  cascade re-solves.
- `default_power_grid()` — the canonical two-area corridor: both generators in
  Area A, pure load in Area B, joined by a strong interconnector and a weak
  tie.
- `grid_connectivity()` — buses reachable from the slack bus. It seeds its
  search *at* the slack bus, so the slack bus is always a member: there is no
  "slack islanded" case, and therefore no guard for one.
- `dc_power_flow()` — the linearised load flow. Builds the susceptance matrix,
  removes the slack row/column, solves `B' theta' = P'`, and reports directed
  line flows `F_ij = b_ij (theta_i - theta_j)`. Only the slack-connected live
  component is solved; islanded buses are dead and their load is unserved.
- `cascade_failure()` — the deterministic outage cascade (OPA paradigm): trip
  the initial line, re-solve, trip the most overloaded survivor, repeat until
  stable or `max_steps`. Returns tripped lines, step count, lost load (MW),
  and the blackout fraction.
- `total_load()`, `grid_fingerprint()` — connected load and a stable dataset
  hash.

### `negotiation_tactics.py` — bargaining under syndrome-driven patience

- `NegotiationParams` — the validated bargaining configuration (discounts,
  deadline, opening demand/offer, concession rate).
- `equilibrium_shares()` / `rubinstein_split()` — the subgame-perfect
  alternating-offer equilibrium `x_c = (1 - d_n)/(1 - d_c d_n)`.
- `captor_discount_from_syndrome()` — the declared modelling assumption that
  links the pillars: identification raises the captor's patience,
  `d_c = clamp(base + gain * S)`.
- `settlement_analysis()` — resolves the concession game in time. Three
  outcomes are distinguished and all are reachable: **stalemate** (equilibrium
  shares disjoint), **deadline** (crossing later than the horizon), and
  **settled** — where the crossing is either the symmetric midpoint or one
  side's equilibrium floor, whichever binds first.

### `sensor_fusion.py` — Kalman tracking of the hijacked hull

- `TrackConfig` — validated scenario (step, count, process/measurement noise,
  seed, initial state).
- `generate_track()` — deterministic constant-velocity truth plus noisy
  position fixes from `numpy.random.default_rng(seed)`.
- `KalmanFilter` — the constant-velocity linear filter: `predict()` propagates
  state and covariance, `update()` applies the gain
  `K = P H^T (H P H^T + R)^-1` and returns the innovation norm.
- `FilterStep` — the per-step record (estimate, covariance trace, innovation)
  the filter emits.
- `track_rmse()`, `run_tracking()` — filter RMSE against the raw-measurement
  baseline, final position error, and the convergence flag.

## Composition: how the pillars couple

The modules are independent, but the *mission* couples three pairs:

| Producer | Consumer | What flows |
| --- | --- | --- |
| `hostage_psychology.integrate_dynamics` | `negotiation_tactics.settlement_analysis` | `final_syndrome` → the captor's discount factor |
| `pipeline_security` (choke points) | `power_grid.cascade_failure` | narrative force multiplier: the cut that blacks out the pumping corridor |
| `sub_defense` (evasion) | `sensor_fusion.run_tracking` | the evading hull that must be re-acquired |

Only the first is a code-level data dependency. It is wired in exactly two
places — `mission._run_steps()` and
`manuscript_variables._run_domain_tokens()` — and both pass the same measured
`final_syndrome`, so the mission outcome and the manuscript agree by
construction.

## `mission.py` — the frozen MissionProvider

`mission.py` is the only module that imports `bond_api`. It is a top-level
`the_world_is_not_enough.mission` module (the discovery contract) exposing a
`MissionProvider` class that satisfies `bond_api.protocol.MissionProvider`.

**The public shape is frozen.** `bond-cli`, the coordinator reconcile, and the
orchestrator consume it across every package in the suite, so the five methods
and the module-level `GADGETS` registry must not change signature. Depth is
added *inside*: more plan steps, more result keys, more gadgets.

| Stage | Returns | What it does here |
| --- | --- | --- |
| `brief()` | `MissionBrief` | Declares film, codename `ELEKTRA`, four objectives, six `Asset` manifests (one per pillar), and three `Constraint`s (determinism, isolation, math). |
| `recon(request)` | `ReconReport` | Seven `Finding`s: the caller's goal plus one measured surface per pillar (node/segment counts, grid size and sensor count, integration horizon, bus/line counts, negotiation deadline, fix count). |
| `plan(brief)` | `MissionPlan` | Eight `Step`s: choke-point analysis, tamper simulation, risk map, evasion routing, hostage integration, cascade blackout, bargaining settlement, submarine tracking. |
| `execute(plan)` | `MissionOutcome` | Runs all eight against the pure cores via `_run_steps()`, returns the measured result keys plus `steps_completed`, wrapped in `Provenance(package_version, seed=1999, input_hash, wall_time_s=0.0)`. |
| `debrief(outcome)` | `Debrief` | Six lessons derived *from the measured outcome dict*, never restated from a literal. |

Supporting pieces:

- `mission_input_hash(plan)` — SHA-256 over the sorted-JSON canonical form of
  `(step.name, step.action, step.params)` plus `_plan_params()`. Two
  executions of the same mission hash identically; this is what makes
  `test_mission.py::TestExecute::test_deterministic` a real assertion rather
  than a tautology.
- Module constants `_PIPELINE`, `_SUB_SENSORS`, `_GRID`, `_NEGOTIATION`,
  `_FUSION`, … mirror the `experiment:` block of `manuscript/config.yaml`, so
  the mission and the manuscript measure the same run. The public identity
  constants are `CODENAME`, `FILM`, `SEED` and `PACKAGE_VERSION`;
  `tests/test_mission.py` asserts the mission's measured results equal the
  manuscript's tokens, so the mirroring cannot drift silently.
- `GADGETS: GadgetRegistry` — built at import by `_build_gadgets()` and
  registering eight callables under the film slug: `pipeline_analysis`,
  `tamper_simulation`, `evasion_analysis`, `hostage_dynamics`,
  `power_cascade`, `negotiation_settlement`, `submarine_tracking`,
  `mission_input_hash`.

`wall_time_s` is always `0.0` and `scripts/execute.py` persists with a fixed
mission epoch, so no clock value ever reaches a result.

## Manuscript and figures

`manuscript_variables.py` exposes `load_manuscript_config()` and
`generate_variables()`, which reads `manuscript/config.yaml` and *runs the
domain models* to compute every `{{TOKEN}}`:

- `_declared_config_tokens()` → the `CONFIG_*` values **typed by the author**
  in the config file; their names are pinned in `DECLARED_CONFIG_TOKENS`.
- `_derived_dataset_tokens()` → the `CONFIG_*` values **read off the fixed
  datasets** (`default_pipeline()`, `default_power_grid()`,
  `CHOKE_UTILIZATION_THRESHOLD`) — derived, never typed, and unmovable from
  the config file; pinned in `DERIVED_DATASET_TOKENS`. `_config_tokens()`
  merges the two, and §5 of the manuscript labels each row with which it is.
- `hostage_params()`, `kindness_events()`, `hostage_initial_state()` → build
  the hostage model's whole parameter surface from
  `experiment.hostage`, so the rate constants the manuscript declares as its
  modelling assumption are genuinely config-driven rather than hardcoded.
- `_run_domain_tokens()` → the `RESULT_*` family (measured outputs).
- `RESULT_TOKEN_UNITS` → the declared physical unit of every result token, and
  `_assert_units_consistent()` → the unit gate: an undeclared token, or a
  token declared as a *rate* whose value exceeds the system's physical ceiling
  (installed pipeline capacity for `kbbl/day`, connected load for `MW`), fails
  hydration. This is what stops a cumulative volume being rendered as a
  per-day rate.
- `_assert_measurable()` → the strict gate: a blank or non-finite token fails
  hydration instead of rendering `nan` as a measured result.
- `resolve_manuscript_tree()` → substitutes into `NN_*.md` and refuses, in
  strict mode, to write a section with a leftover `{{TOKEN}}`.

`figures.py` renders four deterministic figures under headless `Agg` via
`generate_all_figures()`, which calls `figure_pipeline_network()`,
`figure_submarine_detection()`, `figure_hostage_dynamics()` and
`figure_sensor_fusion_track()` to write `pipeline_network.png`,
`submarine_detection.png`, `hostage_dynamics.png` and
`sensor_fusion_track.png`. No timestamps are drawn.

## Scripts

Thin orchestrators only. Each inserts `src/` on `sys.path`, loads the provider
(or calls the figure/token generator), and prints canonical output:
`brief.py`, `recon.py`, `plan.py`, `execute.py`, `debrief.py`,
`generate_figures.py`, `z_generate_manuscript_variables.py`. `execute.py`
additionally persists a provenance record through
`bond_utilities.mission_io.record_provenance_outcome` at the fixed epoch.

## Data flow (reproducibility)

`manuscript/config.yaml` (experiment block) → domain models → measured
`RESULT_*` values → `manuscript_variables.py` → `{{TOKEN}}`s →
`output/manuscript/*.md` + `output/data/manuscript_variables.json`. Figures
derive from the same models. `output/` is git-ignored, so a full regeneration
leaves the tree clean — itself a determinism proof.

## External dependencies

- `bond-api` (frozen protocol, Layer 1) — local path dependency.
- `bond-utilities` (Layer 0, provenance persistence) — local path dependency.

Both resolve from the same local-only suite tree via `[tool.uv.sources]`.

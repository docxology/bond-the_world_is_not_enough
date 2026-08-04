# Testing Philosophy — the_world_is_not_enough (ELEKTRA)

Zero mocks. Every test exercises the real algorithms, models, and CLIs with
real deterministic inputs.

## Core tenets

- **Real data + computation only.** No `MagicMock`, `mocker.patch`,
  `unittest.mock`, or `create_autospec`. Deterministic fakes implement the real
  protocol where needed (none required here — the providers are already real).
- **Meaningful assertions.** Tests check known analytic values (max-flow =
  min-cut, `Phi(0)=0.5`, exponential decay match for RK4, Manhattan-distance
  Dijkstra cost) and hand-constructed graphs, not tautological properties.
- **Determinism is tested.** Two runs with the same seed must produce identical
  outputs; `test_mission.py::TestExecute::test_deterministic` and per-domain
  determinism tests enforce this.
- **Error branches are covered.** Dataclass validation and input
  bounds (`ValueError` / `TypeError`) are asserted for every public entry point.
- **Subprocess smoke.** Phase CLIs are exercised as real subprocesses
  (`sys.executable`, `cwd=root`) to prove they load, run, and emit canonical
  JSON / artifacts.

## Coverage

The enforced gate is **≥90% line+branch on `src/`**:

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
```

Live test count and achieved coverage are tracked in
`../docs/_generated/COUNTS.md` (recompute on meaningful changes).

## Test layout

| File | Exercises |
| --- | --- |
| `test_pipeline_security.py` | flow network, max-flow/min-cut, betweenness, utilization, sensor coverage, tamper sim |
| `test_sub_defense.py` | sonar equation, normal CDF, detection, risk map, Dijkstra evasion, triangulation |
| `test_hostage_psychology.py` | ODE model, RK4, bounds, onset regimes, determinism |
| `test_mission.py` | protocol conformance, full mission, provenance, gadgets, discovery, serialization |
| `test_figures.py` | deterministic figure generation (headless) |
| `test_manuscript_variables.py` | token hydration + live manuscript cross-reference |
| `test_scripts_smoke.py` | real subprocess phase CLIs and artifact scripts |

## Deterministic-input guidance

- Prefer fixed inputs; where a random *risk field* is convenient in a test,
  build it with `np.random.default_rng(seed)` so it is reproducible.
- Do not assert on wall-clock; provenance reports `wall_time_s = 0.0`.

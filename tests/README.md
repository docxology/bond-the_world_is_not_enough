# tests/ — the_world_is_not_enough (ELEKTRA)

Zero-mock test suite.

| File | Exercises |
| --- | --- |
| `test_pipeline_security.py` | flow network, max-flow/min-cut, betweenness, utilization, sensor coverage, tamper sim |
| `test_sub_defense.py` | sonar equation, normal CDF, detection, risk map, Dijkstra evasion, triangulation |
| `test_hostage_psychology.py` | ODE model, RK4, bounds, onset regimes, determinism |
| `test_power_grid.py` | DC power flow, cascading blackout, connectivity, validation |
| `test_negotiation_tactics.py` | Rubinstein equilibrium, syndrome patience, concession settlement |
| `test_sensor_fusion.py` | Kalman predict/update, tracking, RMSE metrics, determinism |
| `test_mission.py` | protocol conformance, full mission (8 steps), provenance, gadgets, discovery, serialization |
| `test_figures.py` | deterministic figure generation (4 figures, headless) |
| `test_manuscript_variables.py` | token hydration + live manuscript cross-reference |
| `test_scripts_smoke.py` | real subprocess phase CLIs and artifact scripts |

See `PATTERNS.md` for shared patterns and `../docs/testing_philosophy.md` for
the philosophy and the coverage gate (`uv run pytest tests/ --cov=src --cov-fail-under=90`).

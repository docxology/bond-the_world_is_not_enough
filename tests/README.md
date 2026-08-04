# tests/ — the_world_is_not_enough (ELEKTRA)

Zero-mock test suite.

| File | Exercises |
| --- | --- |
| `test_pipeline_security.py` | flow network, max-flow/min-cut, betweenness, utilization, sensor coverage, tamper sim |
| `test_sub_defense.py` | sonar equation, normal CDF, detection, risk map, Dijkstra evasion, triangulation |
| `test_hostage_psychology.py` | ODE model, RK4, bounds, onset regimes, determinism |
| `test_mission.py` | protocol conformance, full mission, provenance, gadgets, discovery, serialization |
| `test_figures.py` | deterministic figure generation (headless) |
| `test_manuscript_variables.py` | token hydration + live manuscript cross-reference |
| `test_scripts_smoke.py` | real subprocess phase CLIs and artifact scripts |

See `PATTERNS.md` for shared patterns and `../docs/testing_philosophy.md` for
the philosophy and the coverage gate (`uv run pytest tests/ --cov=src --cov-fail-under=90`).

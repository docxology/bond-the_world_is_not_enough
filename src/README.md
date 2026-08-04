# src/ — the_world_is_not_enough (ELEKTRA)

The domain core and protocol adapter, organized in dependency order.

## Modules

| Module | Layer | Responsibility |
| --- | --- | --- |
| `pipeline_security.py` | pure core | Flow network (17-node Caspian trunk), Edmonds–Karp max-flow/min-cut, Brandes betweenness, capacity utilization, sensor coverage, deterministic tamper simulation, `analyze_choke_points` |
| `sub_defense.py` | pure core | Passive-sonar equation + normal-CDF detection link, risk map, Dijkstra least-risk evasion, bearing triangulation |
| `hostage_psychology.py` | pure core | Four-state Stockholm-syndrome ODE (fear/gratitude/identification/threat) with fixed-step RK4, onset/peak/final + influence metrics |
| `figures.py` | manuscript | Three deterministic concept figures (headless `Agg`) |
| `manuscript_variables.py` | manuscript | `{{TOKEN}}` hydration from `manuscript/config.yaml` + measured outputs |
| `mission.py` | protocol adapter | `ELEKTRA` `MissionProvider` (frozen `bond_api`), `GADGETS` registration |

## Import rules

- Pure core (`pipeline_security`, `sub_defense`, `hostage_psychology`):
  stdlib + numpy/matplotlib only. **No** `bond_api`, **no** `bond_utilities`.
- `figures.py`, `manuscript_variables.py`: may import `yaml` and the pure core.
- `mission.py`: the only module importing `bond_api`.
- The package `__init__.py` exposes only the pure core (bond-free import
  guarantee); `mission.py` is imported explicitly by discovery and scripts.

## Determinism

Fixed seed `1999`; `random.Random` for tamper draws; `wall_time_s=0.0`; no
wall-clock in results. Everything is byte-reproducible.

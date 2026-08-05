# Architecture — the_world_is_not_enough (ELEKTRA)

## Layer boundaries

```
scripts/                       # thin orchestrators (argv shaping + print)
   |  // may import bond_api, bond_utilities, and src/
   v
src/the_world_is_not_enough/
   mission.py                  # ADAPTER: bond_api MissionProvider + gadgets
   manuscript_variables.py     # token hydration (config + measured outputs)
   figures.py                  # deterministic figures (Agg)
   |  // pure, bond-free, deterministic
   v
   pipeline_security.py        # flow network, choke points, tamper sim (numpy-free core)
   sub_defense.py              # sonar equation, Dijkstra evasion (numpy)
   hostage_psychology.py       # ODE model, RK4 (stdlib)
```

### Pure domain core

`pipeline_security.py`, `sub_defense.py`, `hostage_psychology.py`,
`power_grid.py`, `negotiation_tactics.py`, and `sensor_fusion.py` are the
mathematical heart. They are infrastructure-free (stdlib + numpy/matplotlib
only), deterministic, and **importable without `bond_api`**. This is the
layer-contract guarantee: if the protocol dependency were ever unavailable,
the models still run.

### Protocol adapter

The `mission.py` adapter imports `bond_api.protocol` and
`bond_api.registry`. It exposes the top-level `MissionProvider` class
(film = `the_world_is_not_enough`, codename `ELEKTRA`), returns protocol
dataclasses for all five stages, builds a `Provenance` with `seed=1999`,
`wall_time_s=0.0`, and an SHA-256 `input_hash` over the executed plan, and
registers domain callables in the module-level `GADGETS` registry at import
time. Its *public shape* (the protocol methods and the gadget registry
convention) is stable; deeper pillars are added as extra plan steps, result
keys, and gadgets, never as protocol changes.

### Manuscript + figures

`manuscript_variables.py` reads `manuscript/config.yaml` and runs the domain
models to compute every `{{TOKEN}}` (both `CONFIG_*` parameters and
`RESULT_*` measured outputs); `figures.py` renders the three deterministic
figures. Metrics are never hand-authored.

### Scripts

Thin orchestrators. They insert `src/` on `sys.path`, load the provider or
call the figure/token generators, and print canonical output. `scripts/execute.py`
persists a provenance record via `bond_utilities.mission_io.record_provenance_outcome`.

## Data flow (reproducibility)

`manuscript/config.yaml` (fixed experiment block) → domain models →
measured `RESULT_*` values → `manuscript_variables.py` → `{{TOKEN}}`s →
`output/manuscript/*.md` + `output/data/manuscript_variables.json`.
Figures derive from the same models. `output/` is git-ignored (regenerable).

## External dependencies

- `bond-api` (frozen protocol, Layer 1) — local path dependency.
- `bond-utilities` (Layer 0, provenance persistence) — local path dependency.
Both resolve from the same local-only suite tree via `[tool.uv.sources]`.

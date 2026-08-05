# Reproducibility

The ELEKTRA package is deterministic by construction.

## Determinism guarantees

- **Fixed seed.** The package has exactly two stochastic steps and both are
  seeded from the same value (`{{CONFIG_SEED}}`, the film's release year): the
  tamper-event simulation draws from Python's `random.Random`, and the
  sensor-fusion measurement noise from `numpy.random.default_rng`. Every other
  model — max-flow/min-cut, betweenness, the sonar field, Dijkstra routing, the
  RK4 integration, the DC load flow and its cascade, and the bargaining
  equilibrium — makes no random draws at all. Runs are byte-reproducible.
- **No wall-clock anywhere in the persisted artifacts.** The mission outcome's
  `Provenance.wall_time_s` is always `0.0`; persisted provenance records use a
  fixed nominal mission epoch. `MANUSCRIPT_EDITION_STAMP` is the only
  time-valued token and it is *derived* from the committed `paper.date` key in
  `config.yaml` — it is an edition stamp a maintainer edits on purpose, never a
  reading of the clock at generation time. Consequently two regenerations of
  `output/data/manuscript_variables.json` and `output/manuscript/` on one
  interpreter are byte-identical, which
  `tests/test_manuscript_variables.py::TestRegenerationDeterminism` proves by
  running the generator twice across a second boundary and comparing the
  persisted bytes.
- **No external calls.** The pure domain cores never touch the network or the
  filesystem; the only I/O is thin scripts writing regenerable `output/`
  artifacts (git-ignored).
- **Fixed datasets.** Pipeline topology and sensor positions are declared
  constants, not sampled.

## Reproducing every number

```bash
# Mission outcomes (provenance to output/data/elektra_mission.json)
uv run python scripts/execute.py

# Figures -> output/figures/
uv run python scripts/generate_figures.py

# Manuscript variable hydration -> output/data + output/manuscript/
uv run python scripts/z_generate_manuscript_variables.py

# Gate: >=90% line+branch coverage on src/, zero mocks
uv run pytest tests/ --cov=src --cov-fail-under=90
```

A live cross-reference test (`tests/test_manuscript_variables.py`) enforces that
every token used in a numbered manuscript section is actually generated, so the
prose can never present a stale or fabricated metric. Hydration additionally
runs a measurability gate (`_assert_measurable`) that rejects any blank or
non-finite result token, so a degenerate model run fails the build instead of
rendering `nan` as a measured value.

## Artifact inventory

| Artifact | Path | Regenerable |
|---|---|---|
| Mission outcome (canonical JSON) | `output/data/elektra_mission.json` | yes |
| Manuscript variables JSON | `output/data/manuscript_variables.json` | yes |
| Pipeline figure | `output/figures/pipeline_network.png` | yes |
| Submarine figure | `output/figures/submarine_detection.png` | yes |
| Hostage figure | `output/figures/hostage_dynamics.png` | yes |
| Sensor-fusion figure | `output/figures/sensor_fusion_track.png` | yes |
| Resolved manuscript tree | `output/manuscript/` | yes |

`output/` is git-ignored, so regeneration never dirties the tree — but a clean
`git status` is a consequence of the ignore rule, not evidence of determinism.
The evidence is the two-run byte comparison in
`TestRegenerationDeterminism`, which regenerates the JSON and the resolved
manuscript tree into two fresh directories a second apart and asserts every
file matches byte for byte.

# Reproducibility

The ELEKTRA package is deterministic by construction.

## Determinism guarantees

- **Fixed seed.** All random draws — the tamper-event simulation — use a single
  fixed seed (`{{CONFIG_SEED}}`, the film's release year) via Python's
  `random.Random`, so the simulation is byte-reproducible.
- **No wall-clock in results.** The mission outcome's `Provenance.wall_time_s`
  is always `0.0`; persisted provenance records use a fixed nominal mission
  epoch. `GENERATION_TIMESTAMP` is the only time-valued token and is overridable
  (`now=`) for deterministic regeneration.
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
prose can never present a stale or fabricated metric.

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

Because `output/` is git-ignored, a full regeneration leaves the tree clean —
itself a live determinism proof.

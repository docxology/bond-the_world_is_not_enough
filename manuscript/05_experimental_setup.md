# Experimental Setup

Every `{{CONFIG_*}}` token below carries a **Source** column, because the two
kinds are not interchangeable. `config.yaml` marks a value *typed by the
author* in `manuscript/config.yaml`: editing it and re-running
`scripts/z_generate_manuscript_variables.py` re-derives the affected results in
§3. `derived` marks a value *read off a fixed dataset or module constant*
(`default_pipeline()`, `default_power_grid()`,
`CHOKE_UTILIZATION_THRESHOLD`) — those cannot be changed from the config file
at all, and changing them means editing the dataset in the domain module.
The split is enforced in code
(`manuscript_variables.DECLARED_CONFIG_TOKENS` /
`DERIVED_DATASET_TOKENS`) and this table is checked against it by
`tests/test_manuscript_variables.py`, so a mislabelled row fails the suite.

## Table 1 — Scenario parameters

| Parameter | Token | Source | Value |
|---|---|---|---|
| Mission codename | `MISSION_CODENAME` | derived | {{MISSION_CODENAME}} |
| Deterministic seed | `CONFIG_SEED` | config.yaml | {{CONFIG_SEED}} |
| Pipeline nodes | `CONFIG_PIPELINE_NODES` | derived | {{CONFIG_PIPELINE_NODES}} |
| Pipeline segments | `CONFIG_PIPELINE_SEGMENTS` | derived | {{CONFIG_PIPELINE_SEGMENTS}} |
| Choke-point utilization threshold (%) | `CONFIG_CHOKE_UTILIZATION` | derived | {{CONFIG_CHOKE_UTILIZATION}} |
| Tamper attempts | `CONFIG_TAMPER_EVENTS` | config.yaml | {{CONFIG_TAMPER_EVENTS}} |
| Per-sensor interdict probability | `CONFIG_DETECTION_PROBABILITY` | config.yaml | {{CONFIG_DETECTION_PROBABILITY}} |
| Sonar grid size | `CONFIG_SUB_GRID` | config.yaml | {{CONFIG_SUB_GRID}} |
| Sonar cell size (km) | `CONFIG_SUB_STEP_KM` | config.yaml | {{CONFIG_SUB_STEP_KM}} |
| Listening sensors | `CONFIG_SUB_SENSORS` | config.yaml | {{CONFIG_SUB_SENSORS}} |
| Hostage integration horizon (days) | `CONFIG_HOSTAGE_DAYS` | config.yaml | {{CONFIG_HOSTAGE_DAYS}} |
| Hostage integration step | `CONFIG_HOSTAGE_DT` | config.yaml | {{CONFIG_HOSTAGE_DT}} |
| Syndrome onset threshold | `CONFIG_HOSTAGE_ONSET` | config.yaml | {{CONFIG_HOSTAGE_ONSET}} |
| Power-grid buses | `CONFIG_GRID_BUSES` | derived | {{CONFIG_GRID_BUSES}} |
| Power-grid lines | `CONFIG_GRID_LINES` | derived | {{CONFIG_GRID_LINES}} |
| Connected load (MW) | `CONFIG_GRID_LOAD_MW` | derived | {{CONFIG_GRID_LOAD_MW}} |
| Targeted interconnector | `CONFIG_GRID_INITIAL_OUTAGE` | config.yaml | {{CONFIG_GRID_INITIAL_OUTAGE}} |
| Targeted interconnector rating (MW) | `CONFIG_GRID_STRONG_TIE_MW` | derived | {{CONFIG_GRID_STRONG_TIE_MW}} |
| Weak interconnector | `CONFIG_GRID_WEAK_TIE` | derived | {{CONFIG_GRID_WEAK_TIE}} |
| Weak interconnector rating (MW) | `CONFIG_GRID_WEAK_TIE_MW` | derived | {{CONFIG_GRID_WEAK_TIE_MW}} |
| Negotiation deadline (days) | `CONFIG_NEG_DEADLINE_DAYS` | config.yaml | {{CONFIG_NEG_DEADLINE_DAYS}} |
| Negotiator discount | `CONFIG_NEG_NEGOTIATOR_DISCOUNT` | config.yaml | {{CONFIG_NEG_NEGOTIATOR_DISCOUNT}} |
| Concession rate (per day) | `CONFIG_NEG_CONCESSION_RATE` | config.yaml | {{CONFIG_NEG_CONCESSION_RATE}} |
| Captor patience base ($\delta_c$ at $S=0$) | `CONFIG_NEG_CAPTOR_DISCOUNT_BASE` | config.yaml | {{CONFIG_NEG_CAPTOR_DISCOUNT_BASE}} |
| Captor patience gain (per unit $S$) | `CONFIG_NEG_CAPTOR_DISCOUNT_GAIN` | config.yaml | {{CONFIG_NEG_CAPTOR_DISCOUNT_GAIN}} |
| Opening demand | `CONFIG_NEG_INITIAL_DEMAND` | config.yaml | {{CONFIG_NEG_INITIAL_DEMAND}} |
| Opening offer | `CONFIG_NEG_INITIAL_OFFER` | config.yaml | {{CONFIG_NEG_INITIAL_OFFER}} |
| Fusion fix count | `CONFIG_FUSION_STEPS` | config.yaml | {{CONFIG_FUSION_STEPS}} |
| Fusion measurement std | `CONFIG_FUSION_MEASUREMENT_NOISE` | config.yaml | {{CONFIG_FUSION_MEASUREMENT_NOISE}} |

## Table 2 — Hostage-model rate constants

The clinical and forensic literature on Stockholm syndrome is qualitative, so
the nine ODE rate constants below are a **declared modelling assumption**, not
a fitted result (§7). They are typed in `manuscript/config.yaml` under
`experiment.hostage.dynamics` and consumed by
`hostage_psychology.integrate_dynamics`; an auditor can change any one of them
and re-derive every syndrome and bargaining number in §3.

| Rate | Token | Source | Value |
|---|---|---|---|
| Fear self-decay $a$ | `CONFIG_HOSTAGE_FEAR_DECAY` | config.yaml | {{CONFIG_HOSTAGE_FEAR_DECAY}} |
| Threat sensitivity $b$ | `CONFIG_HOSTAGE_THREAT_SENSITIVITY` | config.yaml | {{CONFIG_HOSTAGE_THREAT_SENSITIVITY}} |
| Kindness gain $c$ | `CONFIG_HOSTAGE_KINDNESS_GAIN` | config.yaml | {{CONFIG_HOSTAGE_KINDNESS_GAIN}} |
| Gratitude decay $d$ | `CONFIG_HOSTAGE_GRATITUDE_DECAY` | config.yaml | {{CONFIG_HOSTAGE_GRATITUDE_DECAY}} |
| Identification gain $e$ | `CONFIG_HOSTAGE_IDENT_GAIN` | config.yaml | {{CONFIG_HOSTAGE_IDENT_GAIN}} |
| Fear suppression $f$ | `CONFIG_HOSTAGE_FEAR_SUPPRESS` | config.yaml | {{CONFIG_HOSTAGE_FEAR_SUPPRESS}} |
| Initial threat $T_0$ | `CONFIG_HOSTAGE_THREAT_INITIAL` | config.yaml | {{CONFIG_HOSTAGE_THREAT_INITIAL}} |
| Threat decay $\lambda$ | `CONFIG_HOSTAGE_THREAT_DECAY` | config.yaml | {{CONFIG_HOSTAGE_THREAT_DECAY}} |
| Residual threat floor | `CONFIG_HOSTAGE_THREAT_FLOOR` | config.yaml | {{CONFIG_HOSTAGE_THREAT_FLOOR}} |
| Initial state $(F, G, I)$ | `CONFIG_HOSTAGE_INITIAL_STATE` | config.yaml | {{CONFIG_HOSTAGE_INITIAL_STATE}} |
| Small-kindness schedule | `CONFIG_HOSTAGE_KINDNESS_SCHEDULE` | config.yaml | {{CONFIG_HOSTAGE_KINDNESS_SCHEDULE}} |

## Software environment

- Package version: {{PACKAGE_VERSION}}
- Python: {{PYTHON_VERSION}}
- Manuscript edition stamp (declared in `config.yaml` as `paper.date`, not a
  clock reading): {{MANUSCRIPT_EDITION_STAMP}}

## What is *not* tunable from the config file

Tables 1 and 2 are the complete set of author-typed parameters, but they are
not the complete set of inputs. Three fixed datasets sit outside them and can
only be changed by editing the domain module that declares them:

- the pipeline topology and its per-segment capacities, tamper risks and sensor
  placement (`pipeline_security.default_pipeline()`,
  {{CONFIG_PIPELINE_NODES}} nodes / {{CONFIG_PIPELINE_SEGMENTS}} segments);
- the power-grid topology, line ratings and nodal injections
  (`power_grid.default_power_grid()`, {{CONFIG_GRID_BUSES}} buses /
  {{CONFIG_GRID_LINES}} lines);
- the choke-point utilization threshold
  (`pipeline_security.CHOKE_UTILIZATION_THRESHOLD`).

The sonar sensor mosaic *is* config-typed (`experiment.submarine.sensors`),
though only its count is surfaced as a token. Every row marked `derived` in
Table 1 is a read-out of one of the three datasets above, which is why editing
`config.yaml` cannot move it. Re-running
`scripts/z_generate_manuscript_variables.py` after any of these changes
re-derives every result token in §3, and no file is written outside `output/`.

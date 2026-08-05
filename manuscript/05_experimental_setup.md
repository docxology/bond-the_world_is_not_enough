# Experimental Setup

All experiments are configured in `manuscript/config.yaml` and executed
deterministically; the values below are injected as `{{CONFIG_*}}` tokens from
that file.

## Parameters

| Parameter | Token | Value |
|---|---|---|
| Mission codename | `MISSION_CODENAME` | {{MISSION_CODENAME}} |
| Deterministic seed | `CONFIG_SEED` | {{CONFIG_SEED}} |
| Pipeline nodes | `CONFIG_PIPELINE_NODES` | {{CONFIG_PIPELINE_NODES}} |
| Pipeline segments | `CONFIG_PIPELINE_SEGMENTS` | {{CONFIG_PIPELINE_SEGMENTS}} |
| Choke-point utilization threshold (%) | `CONFIG_CHOKE_UTILIZATION` | {{CONFIG_CHOKE_UTILIZATION}} |
| Tamper attempts | `CONFIG_TAMPER_EVENTS` | {{CONFIG_TAMPER_EVENTS}} |
| Per-sensor interdict probability | `CONFIG_DETECTION_PROBABILITY` | {{CONFIG_DETECTION_PROBABILITY}} |
| Sonar grid size | `CONFIG_SUB_GRID` | {{CONFIG_SUB_GRID}} |
| Sonar cell size (km) | `CONFIG_SUB_STEP_KM` | {{CONFIG_SUB_STEP_KM}} |
| Listening sensors | `CONFIG_SUB_SENSORS` | {{CONFIG_SUB_SENSORS}} |
| Hostage integration horizon (days) | `CONFIG_HOSTAGE_DAYS` | {{CONFIG_HOSTAGE_DAYS}} |
| Hostage integration step | `CONFIG_HOSTAGE_DT` | {{CONFIG_HOSTAGE_DT}} |
| Syndrome onset threshold | `CONFIG_HOSTAGE_ONSET` | {{CONFIG_HOSTAGE_ONSET}} |
| Power-grid buses | `CONFIG_GRID_BUSES` | {{CONFIG_GRID_BUSES}} |
| Power-grid lines | `CONFIG_GRID_LINES` | {{CONFIG_GRID_LINES}} |
| Connected load (MW) | `CONFIG_GRID_LOAD_MW` | {{CONFIG_GRID_LOAD_MW}} |
| Targeted interconnector | `CONFIG_GRID_INITIAL_OUTAGE` | {{CONFIG_GRID_INITIAL_OUTAGE}} |
| Targeted interconnector rating (MW) | `CONFIG_GRID_STRONG_TIE_MW` | {{CONFIG_GRID_STRONG_TIE_MW}} |
| Weak interconnector | `CONFIG_GRID_WEAK_TIE` | {{CONFIG_GRID_WEAK_TIE}} |
| Weak interconnector rating (MW) | `CONFIG_GRID_WEAK_TIE_MW` | {{CONFIG_GRID_WEAK_TIE_MW}} |
| Negotiation deadline (days) | `CONFIG_NEG_DEADLINE_DAYS` | {{CONFIG_NEG_DEADLINE_DAYS}} |
| Negotiator discount | `CONFIG_NEG_NEGOTIATOR_DISCOUNT` | {{CONFIG_NEG_NEGOTIATOR_DISCOUNT}} |
| Concession rate (per day) | `CONFIG_NEG_CONCESSION_RATE` | {{CONFIG_NEG_CONCESSION_RATE}} |
| Fusion fix count | `CONFIG_FUSION_STEPS` | {{CONFIG_FUSION_STEPS}} |
| Fusion measurement std | `CONFIG_FUSION_MEASUREMENT_NOISE` | {{CONFIG_FUSION_MEASUREMENT_NOISE}} |

## Software environment

- Package version: {{PACKAGE_VERSION}}
- Python: {{PYTHON_VERSION}}
- Manuscript variables generated: {{GENERATION_TIMESTAMP}}

The pipeline network topology ({{CONFIG_PIPELINE_NODES}} nodes,
{{CONFIG_PIPELINE_SEGMENTS}} segments), the power-grid topology
({{CONFIG_GRID_BUSES}} buses, {{CONFIG_GRID_LINES}} lines) and the sonar
sensor positions are fixed datasets declared in the domain modules; they are
inputs to the algorithms, not random draws. The table above is the *whole*
tunable surface: changing any row and re-running
`scripts/z_generate_manuscript_variables.py` re-derives every result token in
§3. No file is written outside `output/`.

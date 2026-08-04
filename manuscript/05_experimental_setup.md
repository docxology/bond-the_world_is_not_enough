# Experimental Setup

All experiments are configured in `manuscript/config.yaml` and executed
deterministically; the values below are injected as `{{CONFIG_*}}` tokens from
that file.

## Parameters

| Parameter | Token | Value |
|---|---|---|
| Mission codename | `MISSION_CODENAME` | {{MISSION_CODENAME}} |
| Deterministic seed | `CONFIG_SEED` | {{CONFIG_SEED}} |
| Tamper attempts | `CONFIG_TAMPER_EVENTS` | {{CONFIG_TAMPER_EVENTS}} |
| Per-sensor interdict probability | `CONFIG_DETECTION_PROBABILITY` | {{CONFIG_DETECTION_PROBABILITY}} |
| Sonar grid size | `CONFIG_SUB_GRID` | {{CONFIG_SUB_GRID}} |
| Listening sensors | `CONFIG_SUB_SENSORS` | {{CONFIG_SUB_SENSORS}} |
| Hostage integration horizon (days) | `CONFIG_HOSTAGE_DAYS` | {{CONFIG_HOSTAGE_DAYS}} |
| Hostage integration step | `CONFIG_HOSTAGE_DT` | {{CONFIG_HOSTAGE_DT}} |
| Syndrome onset threshold | `CONFIG_HOSTAGE_ONSET` | {{CONFIG_HOSTAGE_ONSET}} |

## Software environment

- Package version: {{PACKAGE_VERSION}}
- Python: {{PYTHON_VERSION}}
- Manuscript variables generated: {{GENERATION_TIMESTAMP}}

The pipeline network topology (17 nodes, 16 segments) and the sonar sensor
positions are fixed datasets declared in the domain modules; they are inputs to
the algorithms, not random draws. No file is written outside `output/`.

# src/ — agent rules

Repository-wide agent rules live in [`../docs/agent_instructions.md`](../docs/agent_instructions.md)
and the root [`../AGENTS.md`](../AGENTS.md). Directory-specific guidance:

- **`pipeline_security.py`, `sub_defense.py`, `hostage_psychology.py`** are the
  pure domain core: deterministic, infrastructure-free, importable without
  `bond_api`. Do not add protocol or suite imports here.
- **`mission.py`** is the only module that imports `bond_api`; it implements
  the frozen `MissionProvider` and registers gadgets. Keep it thin — dispatch
  to the pure core, don't move logic into it.
- **`manuscript_variables.py`** is the single source of manuscript numbers;
  never hand-author metrics in prose.
- **`figures.py`** must stay headless (`Agg`) and deterministic.

When adding a module, preserve the layer contract (see `../manuscript/layer_contract.yaml`)
and the coverage gate (`uv run pytest tests/ --cov=src --cov-fail-under=90`).

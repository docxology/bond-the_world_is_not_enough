# COUNTS — the_world_is_not_enough (ELEKTRA)

Live, measured counts for this package. Every row below was read off a real
run of the commands in the "Regenerate" section — do not hand-edit a value,
and do not let prose elsewhere in the package restate one.

| Metric | Value |
| --- | --- |
| Test count (pytest, 0 failed / 0 skipped) | 405 |
| Line + branch coverage on `src/` | 100.00% (gate: ≥90%) |
| Coverage gate | `uv run pytest tests/ --cov=src --cov-fail-under=90` |
| Mocks | 0 (no `unittest.mock` / `MagicMock` / `mocker.patch` / `monkeypatch`) |
| Domain modules (pure) | 6 (`pipeline_security`, `sub_defense`, `hostage_psychology`, `power_grid`, `negotiation_tactics`, `sensor_fusion`) |
| Support modules | 3 (`mission`, `manuscript_variables`, `figures`) |
| MissionProvider stages | 5 (brief, recon, plan, execute, debrief) |
| Mission plan steps | 8 |
| Mission result keys | 29 |
| Debrief lessons (derived from the outcome) | 6 |
| Registered gadgets | 8 |
| Manuscript tokens generated | 76 (39 `CONFIG_*` — 30 declared in `config.yaml`, 9 derived from module datasets — plus 30 `RESULT_*` and 7 identity/environment) |
| Manuscript sections | 9 (`00`–`07` plus `99_references`) |
| Concept figures | 4 |
| ruff / mypy | ruff clean on `src/`, `scripts/`, `tests/`; mypy clean on `src/`, `scripts/` |

## Regenerate

```bash
# test count + coverage (the two headline rows)
uv run pytest tests/ --cov=src --cov-fail-under=90 -q | tail -3

# token counts (writes output/data/manuscript_variables.json)
uv run python scripts/z_generate_manuscript_variables.py

# figures
uv run python scripts/generate_figures.py

# structural counts: plan steps, result keys, gadgets
uv run python -c "import sys; sys.path.insert(0, 'src'); \
from the_world_is_not_enough import mission; p = mission.MissionProvider(); \
plan = p.plan(p.brief()); print(len(plan.steps), len(p.execute(plan).results), \
len(mission.GADGETS.gadgets_for(mission.FILM)))"
```

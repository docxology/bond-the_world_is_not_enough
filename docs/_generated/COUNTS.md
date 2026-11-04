# COUNTS — the_world_is_not_enough (ELEKTRA)

Live, measured counts for this package. Every row below was read off a real
run of the commands in the "Regenerate" section — do not hand-edit a value,
and do not let prose elsewhere in the package restate one.

Measured 2026-11-04 on Python 3.15.1 with the locked tools (ruff 0.16.1,
mypy 2.3.0), after `bond-api` and `bond-utilities` moved to the recorded copies
under `vendor/`.

| Metric | Value |
| --- | --- |
| Test count (pytest, 0 failed / 0 skipped) | 406 |
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
| Output files regenerated | 15 |
| ruff / mypy | ruff clean on `src/`, `scripts/`, `tests/`; mypy clean on `src/`, `scripts/` (18 source files) |
| Recorded dependency copies | `scripts/vendor.py --check` → `vendor/bond-api: ok`, `vendor/bond-utilities: ok`, 0 findings |

Two measurement caveats, both recorded in TODO's wave section:

* The regeneration digest is byte-identical only with `PYTHONHASHSEED=0`. Under
  the default interpreter `output/figures/pipeline_network.png` differs on
  every run, because `figures.py` places intermediate nodes with `hash(node)`.
  That is row W5's defect, with its own change.
* A whole-tree `mypy .` run reports **31 errors in 5 files** (34 checked) at
  both the pre-change and post-change heads — outside the documented gate,
  which is `mypy src/ scripts/`.
* A whole-tree `ruff format --check .` and `ruff check .` are clean **because**
  `extend-exclude = ["vendor"]` is in `pyproject.toml`: without that one line
  the check reports 11 findings and the formatter 8 more files, all in
  `vendor/` (measured; row W4).

## Regenerate

```bash
# test count + coverage (the two headline rows)
uv run pytest tests/ --cov=src --cov-fail-under=90 -q | tail -3

# token counts (writes output/data/manuscript_variables.json)
uv run python scripts/z_generate_manuscript_variables.py

# figures (see the determinism caveat above)
uv run python scripts/generate_figures.py

# structural counts: plan steps, result keys, gadgets
uv run python -c "import sys; sys.path.insert(0, 'src'); \
from the_world_is_not_enough import mission; p = mission.MissionProvider(); \
plan = p.plan(p.brief()); print(len(plan.steps), len(p.execute(plan).results), \
len(mission.GADGETS.gadgets_for(mission.FILM)))"

# recorded dependency copies (offline; also run by the suite)
uv run python scripts/vendor.py --check
```

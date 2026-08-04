# Agent Instructions — the_world_is_not_enough (ELEKTRA)

Operational constraints for AI agents and maintainers working in this package.

## Read first

- This package is a PROJECT BOND film package. Scope is **exactly** this
  directory; do not modify siblings, bond root files, or the template repo.
- `../AGENTS.md` (root) carries the hard rules. `testing_philosophy.md`
  governs how tests are written. `architecture.md` governs layer boundaries.

## Working here

1. **Domain core stays pure.** `pipeline_security.py`, `sub_defense.py`, and
   `hostage_psychology.py` must not import `bond_api` or `bond_utilities`; they
   import stdlib + numpy/matplotlib only and are deterministic. This preserves
   the fallback if the path dependency ever fails.
2. **`mission.py` is the only bond_api import.** It implements the frozen
   `MissionProvider` and registers gadgets. Keep it thin.
3. **Determinism is first-class.** Fixed seed (`1999`), no untracked RNG, no
   wall-clock in results. `Provenance.wall_time_s` stays `0.0`; persisted
   records use a fixed mission epoch.
4. **Metrics are tokens.** Any number that appears in the manuscript must come
   from `manuscript_variables.py` (which reads `manuscript/config.yaml` and
   runs the models). Do not hand-author metrics in prose.
5. **Scripts are thin.** Business logic lives in `src/`; scripts bootstrap
   `sys.path` and print canonical BOND-API JSON.

## Guardrails (run before declaring done)

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format src/ scripts/ tests/
uv run mypy src/ scripts/
rg -n "template[_]code_project" . --glob '!uv.lock' --glob '!.git/**' || echo clean
git status --short   # clean after commit
```

## Determinism expectations

- Tamper simulation uses `random.Random(seed)` — reproducible for a fixed seed.
- The sonar risk map and evasion routing make no random draws.
- Graphics use headless `Agg`; figures carry no timestamps.
- Two runs of `scripts/execute.py` produce byte-identical outcomes and
  provenance (`input_hash` equal).

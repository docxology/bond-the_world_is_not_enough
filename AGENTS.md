# AGENTS.md — the_world_is_not_enough (ELEKTRA)

This is an active BOND suite film package under `projects/working/bond/`.
Scope is **exactly this package directory** — never touch sibling packages,
bond root files, or the template repo.

## Identity

- Film: **The World Is Not Enough** (1999)
- Mission codename: **ELEKTRA**
- BOND-API contract: `src/the_world_is_not_enough/mission.py` implements the
  **frozen** `bond_api.MissionProvider` protocol (do not modify the protocol;
  bond-api is FRZ).
- Discovery: top-level module `the_world_is_not_enough.mission` exposing
  `MissionProvider` (loaded by slug on `sys.path`).

## Layer contract

| Surface | Rule |
| --- | --- |
| `pipeline_security.py`, `sub_defense.py`, `hostage_psychology.py`, `power_grid.py`, `negotiation_tactics.py`, `sensor_fusion.py` (in `src/the_world_is_not_enough/`) | Pure domain core — stdlib + numpy/matplotlib only; **no** `bond_api` import; deterministic |
| `src/the_world_is_not_enough/mission.py` | Thin adapter — imports `bond_api.protocol` + `bond_api.registry`; returns protocol dataclasses; `Provenance.wall_time_s = 0.0`; registers gadgets |
| `src/the_world_is_not_enough/figures.py`, `manuscript_variables.py` | Deterministic figures + token hydration from `manuscript/config.yaml` + measured outputs |
| `scripts/` | Thin orchestrators — may import `bond_api`, `bond_utilities`, and the package; business logic stays in `src/` |

## Hard rules

- **Local-only.** No remote, never push. Commits are path-scoped inside this
  repo only.
- **No mocks.** Real data + computation only; deterministic fakes implementing
  the real protocol.
- **≥90% line+branch coverage on `src/`.**
  ```bash
  uv run pytest tests/ --cov=src --cov-fail-under=90
  ```
- **Deterministic.** Fixed seed (`1999`); no untracked RNG; no wall-clock in
  any persisted artifact (`wall_time_s = 0.0`; fixed mission epoch for
  persisted records; `MANUSCRIPT_EDITION_STAMP` derived from the committed
  `paper.date`, never `datetime.now()`). Regenerating `output/` twice must be
  byte-identical.
- **Lint + types.** `uv run ruff check src/ scripts/ tests/`,
  `uv run ruff format src/ scripts/ tests/`, `uv run mypy src/ scripts/`.
- **Metrics are tokens.** Never hand-author numbers in prose; they flow through
  `src/the_world_is_not_enough/manuscript_variables.py` from
  `manuscript/config.yaml` plus measured model outputs.
- **Lineage.** No leftover `template[_]code_project` strings (aim zero); any
  verification-check greps use bracket-split patterns so docs cannot trip
  their own gate.
- Docs (README, AGENTS, TODO) reflect this package.

## Protocol integration

`bond-api` and `bond-utilities` are local path dependencies
(`[tool.uv.sources]`) from the same suite tree. The domain core stays
importable without `bond_api`; `mission.py` is the only module that imports it.
Gadgets (`pipeline_analysis`, `tamper_simulation`, `evasion_analysis`,
`hostage_dynamics`, `power_cascade`, `negotiation_settlement`,
`submarine_tracking`, `mission_input_hash`) are registered at import in the
module-level `GADGETS` registry for the orchestrator to discover.

## Build / test / verify

Setup once (`bond-api` and `bond-utilities` resolve as local path
dependencies from the same suite tree):

```bash
uv sync --extra dev
```

Run the mission, the figures, and the manuscript hydration:

```bash
uv run python scripts/brief.py      # also recon.py / plan.py / execute.py / debrief.py
uv run python scripts/generate_figures.py
uv run python scripts/z_generate_manuscript_variables.py
```

Full verification — all five must pass before a commit lands:

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format --check src/ scripts/ tests/
uv run mypy src/ scripts/
uv run python scripts/z_generate_manuscript_variables.py   # strict token gate
rg -n "template[_]code_project" . --glob '!uv.lock' --glob '!.git/**' || echo clean
git status --short   # clean after commit
```

`uv` cannot write its cache under a restrictive sandbox. A
`Failed to initialize cache` error is an environment restriction, not a
package failure — re-run with the sandbox disabled.

Measured counts (tests, coverage, tokens, steps) live in
[`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md) and are regenerated
from a real run, never hand-edited.

## See also

- `docs/agent_instructions.md` — operational constraints (read before editing)
- `docs/architecture.md` — module-by-module architecture and the frozen
  `MissionProvider` surface
- `docs/testing_philosophy.md` — zero-mock doctrine and what a real assertion
  looks like here
- `docs/_generated/COUNTS.md` — measured counts
- `manuscript/config.yaml` — the deterministic experiment block
- `TODO.md` — remaining work

# Agent Instructions — the_world_is_not_enough (ELEKTRA)

Operational constraints for AI agents and maintainers working in this package.

## Read first

- This package is a PROJECT BOND film package. Scope is **exactly** this
  directory; do not modify siblings, bond root files, or the template repo.
- The suite tree is local-only: this package's only remote is its GitHub
  publish mirror (`origin`). Commit here; never push into a sibling package
  or the suite root.
- `../AGENTS.md` (root) carries the hard rules. `testing_philosophy.md`
  governs how tests are written. `architecture.md` describes every module.

## The five constraints that actually bite

### 1. The domain core stays pure

All six pillar modules — `pipeline_security.py`, `sub_defense.py`,
`hostage_psychology.py`, `power_grid.py`, `negotiation_tactics.py`, and
`sensor_fusion.py` — import stdlib plus numpy only. **None of them may import
`bond_api` or `bond_utilities`**, and none of them import each other. This is
the layer-contract guarantee: if the protocol path dependency ever fails to
resolve, the mathematics still runs and the tests still bind.

Composition belongs one layer up. The one real cross-pillar data dependency
(`hostage_psychology.final_syndrome` → the captor's discount factor in
`negotiation_tactics`) is wired in exactly two places,
`mission._run_steps()` and `manuscript_variables._run_domain_tokens()`, and
both must pass the *same* measured value so the mission outcome and the
manuscript cannot disagree.

### 2. `mission.py` is frozen at the surface

`mission.py` is the only module importing `bond_api`. Its `MissionProvider`
methods (`brief` / `recon` / `plan` / `execute` / `debrief`) and the
module-level `GADGETS` registry are consumed across packages by `bond-cli`,
the coordinator reconcile, and the orchestrator. **Do not change their public
shape.** Deepen inside: add plan steps, add result keys, add gadget entries.
Do not rename a method, change a signature, or move `GADGETS`.

Concretely, `plan()` currently emits eight steps and `execute()` returns their
measured results plus `steps_completed`. Adding a ninth pillar means a ninth
`Step`, more result keys, and a new gadget entry — not a protocol change.

### 3. Determinism is first-class

- Fixed seed (`1999`, the film's release year). Exactly two steps are
  stochastic and both are seeded: the tamper simulation
  (`random.Random(seed)`) and the fusion measurement noise
  (`numpy.random.default_rng(seed)`). Everything else makes no random draws.
- No wall-clock in *any* persisted artifact. `Provenance.wall_time_s` stays
  `0.0`; persisted records use the fixed mission epoch in `scripts/execute.py`.
  `MANUSCRIPT_EDITION_STAMP` is the only time-valued token and is derived from
  the committed `paper.date` key by
  `manuscript_variables.edition_stamp()` — never from `datetime.now()`. Do not
  reintroduce a clock reading behind a `now=` override: an injectable clock
  makes the *test* deterministic while leaving the shipped artifact
  nondeterministic, which is exactly how this breach survived a green suite.
- Two runs of `scripts/execute.py` must produce byte-identical outcomes and an
  identical `input_hash`; two runs of
  `scripts/z_generate_manuscript_variables.py` must produce byte-identical
  `output/` artifacts. Both are enforced by tests, the latter by
  `tests/test_manuscript_variables.py::TestRegenerationDeterminism`.
- Graphics use headless `Agg`; figures carry no timestamps.

### 4. Metrics are tokens

Any number that appears in the manuscript must come from
`manuscript_variables.py`, which reads `manuscript/config.yaml` and *runs the
models*. Never hand-author a metric in prose — not in the manuscript, not in
`README.md`, not in these docs.

To add a measured claim: add the value to `_run_domain_tokens()` (or
`_config_tokens()` for a parameter or a dataset-derived quantity), reference it
as `{{TOKEN}}` in a numbered section, and the live cross-reference test plus
the strict-mode resolver will keep the two in sync. Quantities that describe
the fixed datasets (node counts, interconnector ratings, connected load) are
**derived from the model objects**, never typed as literals.

Markdown source is not a Python string: write `$\theta$`, `\quad`, `\hat{x}`
with a single backslash. A doubled `\\` inside inline math is a LaTeX line
break and renders as a broken formula.

### 5. Scripts are thin

Business logic lives in `src/`. Scripts bootstrap `sys.path`, call into the
package, and print canonical BOND-API JSON or write regenerable artifacts
under `output/`. If you find yourself computing in `scripts/`, the code
belongs in a module.

## Guardrails (run before declaring done)

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

## Things that have actually gone wrong here

Recorded so they are not reintroduced:

- A branch in `dc_power_flow` guarding "slack bus islanded" was dead by
  construction (`grid_connectivity` seeds its search at the slack bus) *and*
  silently returned an empty flow map. Removed. Do not add a guard for a state
  the algorithm cannot enter.
- The manuscript hydration gate checked only that a hardcoded key was present
  in a dict the same function had just built — green by construction. It now
  rejects blank and non-finite tokens and is tested against a corrupted real
  token map.
- §2.4–2.6 of the methodology carried `\\theta`, `\\delta`, `\\quad` — Python
  string escaping leaked into markdown, silently breaking the rendered math.
- `hostage_psychology.math_exp` was a wrapper around `math.exp` whose only
  test asserted `exp(0) == 1`. Both removed; the threat schedule is now
  asserted against its closed form.

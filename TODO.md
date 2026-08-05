# TODO — the_world_is_not_enough (ELEKTRA)

Remaining work only. What is already built is described in
[`README.md`](README.md) (package surface) and
[`docs/architecture.md`](docs/architecture.md) (module by module); measured
counts live in [`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md). This
file does not duplicate any of that.

## Open — model extensions

These are genuine follow-ups, each a scoped piece of work, not aspirations.

- **Frequency-dependent sonar propagation.** `sub_defense.passive_sonar_snr`
  uses spherical spreading plus a single absorption coefficient. A
  frequency-banded transmission-loss model (Thorp absorption, or a simple
  bottom-bounce term) would change the shape of the risk field and therefore
  the routed path. Requires a new `Sensor` field and a scope-section update.
- **Parallel cascade tripping.** `power_grid.cascade_failure` trips the single
  most-overloaded line per step. Real cascades trip every overloaded line in a
  time step. The sequential rule makes the reported blackout a conservative
  lower bound; implementing the parallel variant as an option (and reporting
  both) would remove that caveat from
  `manuscript/07_scope_and_related_work.md`.
- **Bearing-only target-motion analysis.** `sensor_fusion` fuses noisy
  *position* fixes because bearing-only tracking from a stationary observer is
  scale-ambiguous. Batch least-squares TMA from a manoeuvring observer would
  make the pillar match the film's geometry more honestly. This is the largest
  of the three.
- **Asymmetric-information bargaining.** `negotiation_tactics` assumes both
  parties know both discount factors. A one-sided-uncertainty variant would
  make the stalemate threshold a distribution rather than a point.

## Open — modelling assumptions to revisit

- **Syndrome → patience mapping.** `captor_discount_from_syndrome` is a
  declared linear assumption (`clamp(base + gain * S)`), not a fitted
  relationship. It is the only cross-pillar data dependency in the package, so
  it carries real weight in §3.5. If bargaining-under-duress data becomes
  available, replace the mapping and re-derive; until then it must stay
  labelled as an assumption in the scope section.
- **Hostage-model parameters.** Calibrated by construction to reproduce onset
  behaviour, not fitted to case data. Exposed in `manuscript/config.yaml` for
  audit. Same rule: if it is ever fitted, the scope section changes with it.

## Open — small, mechanical

- **Residual uncovered branches.** A handful of defensive `continue` branches
  in `pipeline_security` (visited-node skips) and `power_grid` (empty-active
  break) are unexercised. They are cheap to cover; decide per branch whether
  the honest move is a test or a deletion.
- **`_config_tokens` duplication.** The tokens mirroring `mission.py`'s module
  constants are declared in two places (the config block and the adapter
  constants). They are asserted equal by the manuscript tests, but a single
  source would be better than a tested duplicate.

## Integration points (no action needed here)

- **Orchestrator binding.** The package is discoverable by slug
  (`the_world_is_not_enough.mission.MissionProvider`) and registers `GADGETS`
  at import. A bond-orchestrator run consumes both via `bond_api.discovery`
  and `GadgetRegistry`. The public shape is frozen — see
  [`docs/agent_instructions.md`](docs/agent_instructions.md).
- **Provenance helper.** Persistence is bound to
  `bond_utilities.mission_io.record_provenance_outcome`. If bond-utilities'
  API changes, re-sync the single call site in `scripts/execute.py`.

## Done — do not re-open

Recorded so a future pass does not re-litigate them:

- Six pillars implemented, tested, and written into the manuscript
  (§2.1–2.6 / §3.1–3.6) with every metric arriving as a `{{TOKEN}}`.
- Dead "slack bus islanded" branch removed from `dc_power_flow`; the guard was
  unreachable *and* silently returned an empty flow map.
- Manuscript hydration gate rewritten from a green-by-construction key check
  into a real blank/non-finite rejection, with tests that fail it.
- Escaped-backslash LaTeX corruption fixed in methodology §2.4–2.6.
- `hostage_psychology.math_exp` (a `math.exp` wrapper with a tautological
  test) removed.

## Guardrails

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format --check src/ scripts/
uv run mypy src/ scripts/
uv run python scripts/z_generate_manuscript_variables.py   # strict token gate
rg -n "template[_]code_project" . --glob '!uv.lock' --glob '!.git/**' || echo clean
```

All five must pass before a commit lands. The coverage floor is 90%; the
achieved figure is recorded in `docs/_generated/COUNTS.md`, not quoted here.

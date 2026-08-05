# docs/ — the_world_is_not_enough (ELEKTRA)

Documentation for the ELEKTRA film package: *The World Is Not Enough* (1999)
rendered as deterministic special-agent mission software across six pillars —
oil-pipeline choke-point security, passive-sonar evasion, Stockholm-syndrome
dynamics, DC power flow with cascading blackout, Rubinstein bargaining under
syndrome-driven patience, and Kalman tracking of the hijacked submarine.

This directory holds the *explanatory* documentation. The package root holds
the operational entry points (`../README.md` for setup and usage,
`../AGENTS.md` for the hard rules, `../TODO.md` for remaining work), and
`../manuscript/` holds the paper itself.

## What is here

| File | Read it when you need |
| --- | --- |
| `README.md` | This index — what the docs directory holds and where to start |
| `agent_instructions.md` | The operational constraints before you change anything (read first) |
| `architecture.md` | Module-by-module description of `src/`, how the six pillars compose, and how `mission.py` implements the frozen `bond_api` `MissionProvider` |
| `testing_philosophy.md` | Why there are no mocks, what a meaningful assertion looks like here, and how the coverage gate is enforced |
| `AGENTS.md` | Directory-scoped agent rules for editing these files |
| `_generated/COUNTS.md` | Live measured test count, coverage, module and section counts |

## Suggested reading order

1. `agent_instructions.md` — the constraints (pure core, frozen protocol,
   determinism, tokens-not-numbers).
2. `architecture.md` — what each of the nine modules in
   `src/the_world_is_not_enough/` actually computes.
3. `testing_philosophy.md` — how to add a test that binds truth rather than
   shape.
4. `../manuscript/README.md` — the token protocol and the section map.

## The numbers rule

No measured value is written by hand — not in the manuscript, and not here.
Metrics live in code (`src/the_world_is_not_enough/manuscript_variables.py`)
and in `manuscript/config.yaml`; prose in this directory describes the *gate*
that produces a number and points at the artifact path, rather than quoting a
figure that will silently go stale. The one exception is
`_generated/COUNTS.md`, which exists to carry measured counts and is
regenerated from a real run.

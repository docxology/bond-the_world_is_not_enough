# data/ — the_world_is_not_enough (ELEKTRA)

Small declarative data overlays.

| File | Purpose |
| --- | --- |
| `claim_ledger.yaml` | Registers sourced/computed numeric claims for evidence validation |
| `README.md`, `AGENTS.md` | This directory |

The heavier mission datasets (pipeline topology, sensor positions) live as
constants in the domain modules (`src/`) by design — close to the code that
consumes them and deterministic.

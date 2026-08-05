# data/ — the_world_is_not_enough (ELEKTRA)

Small declarative data overlays.

| File | Purpose |
| --- | --- |
| `claim_ledger.yaml` | Registers computed numeric claims; **enforced** by `tests/test_claim_ledger.py`, which asserts each recorded value equals the live value of the token it cites |
| `README.md`, `AGENTS.md` | This directory |

The heavier mission datasets (pipeline topology, sensor positions) live as
constants in the domain modules (`src/`) by design — close to the code that
consumes them and deterministic.

# docs/ — agent rules

Directory-scoped rules for editing files under `docs/`. The package-wide hard
rules live in [`../AGENTS.md`](../AGENTS.md); the operational constraints for
changing code live in [`agent_instructions.md`](agent_instructions.md). Those
win on conflict.

## What each file is responsible for

- `architecture.md` — the layer boundaries (pure core / protocol adapter /
  thin scripts) **and** a module-by-module account of what every file in
  `src/the_world_is_not_enough/` computes. If you add, rename, or delete a
  module, this file is wrong until you update it.
- `testing_philosophy.md` — the zero-mock doctrine, the coverage gate, and the
  per-file test map. If you add a test module, add its row.
- `agent_instructions.md` — the constraints to read before touching code.
- `README.md` — the index; keep the table in sync with the actual files.
- `_generated/COUNTS.md` — measured counts only. Regenerate it from a real
  run; never edit a number into it by hand.

## Rules for writing here

1. **Describe what exists, not what was planned.** These docs are read by
   agents that will act on them. A module named here must exist in `src/`; a
   command quoted here must run as written. Verify before you write.
2. **No hand-authored metrics.** Coverage percentages, test counts, and model
   results go stale silently. Describe the gate
   (`uv run pytest tests/ --cov=src --cov-fail-under=90`) or point at
   `_generated/COUNTS.md`. The single exception is `_generated/COUNTS.md`
   itself, which is regenerated from measurement.
3. **Keep the frozen surface labelled as frozen.** Anywhere `mission.py`'s
   `MissionProvider` methods or the module-level `GADGETS` registry are
   described, say that the public shape is consumed across packages by
   `bond-cli`, the coordinator, and the orchestrator, and must not change.
4. **Markdown only.** No HTML for content markdown supports.
5. **Stay in scope.** Nothing in this directory should describe a sibling
   BOND package, bond root files, or the template repo.

## After a code change

Re-read `architecture.md` and `testing_philosophy.md` against the tree and fix
whatever drifted, then refresh `_generated/COUNTS.md` from a real run:

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90 -q | tail -3
```

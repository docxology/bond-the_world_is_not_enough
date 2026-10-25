# scripts/ — agent rules

Repository-wide rules live in `../docs/agent_instructions.md` and `../AGENTS.md`.

- Keep scripts thin; dispatch to `src/` (see `../docs/architecture.md`).
- Scripts may import `bond_api`, `bond_utilities`, and the package `src`.
- Every phase script should stay runnable standalone
  (`uv run python scripts/<name>.py`) and exit `0` on success (smoke-tested in
  `tests/test_scripts_smoke.py`).
- Do not duplicate business logic here.

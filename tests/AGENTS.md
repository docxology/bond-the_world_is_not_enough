# tests/ — agent rules

Repository-wide rules live in `../docs/testing_philosophy.md` and `../AGENTS.md`.

- **Zero mocks.** Real data + computation only — no mock framework, no object
  patching, no autospec fakes.
- Enforce the coverage gate on `src/`:
  ```bash
  uv run pytest tests/ --cov=src --cov-fail-under=90
  ```
- Keep every public dataclass/function's validation branches covered
  (`ValueError`/`TypeError` on bad input).
- Figure tests render headless (`Agg`) into `tmp_path`.
- `conftest.py` sets `MPLBACKEND=Agg` and inserts `src/` onto `sys.path`;
  `bond-api`/`bond-utilities` arrive as installed deps.

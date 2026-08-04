# src/STYLE.md

- **Ruff** (88-char line length): `uv run ruff format src/` and
  `uv run ruff check src/`.
- Type hints + docstrings on all public functions and dataclasses; `__all__`
  lists the public surface.
- Pure functions over classes where possible; dataclasses for structured data.
- Determinism first: no hidden RNG, no wall-clock in results, no I/O in core.
- Match neighbour module conventions (numpy where grids are involved, stdlib
  otherwise).

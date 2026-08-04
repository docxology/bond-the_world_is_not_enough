# docs/ — agent rules

Repository-wide agent rules for this package live in
[`../docs/agent_instructions.md`](../docs/agent_instructions.md) and the root
[`../AGENTS.md`](../AGENTS.md). This directory holds targeted guides:

- `architecture.md` — layer boundaries (pure core vs protocol adapter vs thin
  scripts);
- `testing_philosophy.md` — zero-mock testing conventions and the coverage
  gate;
- `agent_instructions.md` — operational constraints to read before modifying
  the package.

Changes here should stay consistent with `src/`, `scripts/`, and `manuscript/`;
metrics always flow through `manuscript_variables.py`, never hand-authored in
docs.

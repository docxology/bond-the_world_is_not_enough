# scripts/ — conventions

- **Thin only.** Scripts shape argv, bootstrap `sys.path`, delegate to `src/`,
  and print. Any substantial algorithm belongs in `src/`.
- **Self-bootstrapping.** Each script inserts its package `src/` into
  `sys.path` before importing (import lines carry `# noqa: E402` where the
  local ruff config does not already exempt E402).
- **Deterministic.** Canonical JSON output via `bond_api.serialization.to_json`;
  no timestamps in printed payloads.
- **Exit codes.** `0` on success; a raising failure exits non-zero.
- Phase scripts mirror the mission lifecycle: brief → recon → plan → execute →
  debrief.

# manuscript/ — agent rules

Repository-wide rules live in `../docs/agent_instructions.md` and `../AGENTS.md`.

- **Metrics are tokens.** Numbers come from
  `src/the_world_is_not_enough/manuscript_variables.py` (config + measured
  outputs), never hand-authored in prose.
- **Adding a token**: add it to `generate_variables()` (or `_config_tokens` /
  `_run_domain_tokens`), use it in a section, and the live cross-reference test
  (`tests/test_manuscript_variables.py`) guards completeness.
- **Do not put literal `{{PLACEHOLDER}}` tokens in numbered sections** — the
  cross-reference gate flags them as unresolved. Illustration of the token
  mechanism belongs in `SYNTAX.md` (not scanned).
- **Figures**: reference via pandoc-crossref `@fig:label`; generate with
  `scripts/generate_figures.py` into `output/figures/` (git-ignored).
- Re-render the scored manuscript (`z_generate_manuscript_variables.py`) after
  changing sections or `config.yaml`.

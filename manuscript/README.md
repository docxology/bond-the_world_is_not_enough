# manuscript/ — the_world_is_not_enough (ELEKTRA)

Token-hydrated manuscript. `config.yaml` carries the paper identity and the
deterministic experiment block; every numeric value is injected as a
`{{TOKEN}}` by `src/the_world_is_not_enough/manuscript_variables.py`.

| File | Role |
| --- | --- |
| `config.yaml` | Paper identity + experiment parameters (source of truth) |
| `config.yaml.example` | Reference copy for new projects |
| `00_abstract.md` … `07_scope_and_related_work.md` | Manuscript sections |
| `99_references.md`, `references.bib` | Bibliography |
| `SYNTAX.md` | Pandoc/crossref/token syntax |
| `layer_contract.yaml` | Declared layer boundaries |
| `preamble.md` | LaTeX injections for PDF rendering |

## Token protocol

- Numeric and mission values are never hand-authored. They flow through
  `manuscript_variables.py` (reads `config.yaml` + runs the models).
- The live cross-reference test (`tests/test_manuscript_variables.py`) fails if
  any `{{TOKEN}}` in a numbered section is not generated.
- Figures are referenced via pandoc-crossref labels `[@fig:...]`
  (`#fig:pipeline_network`, `#fig:submarine_detection`,
  `#fig:hostage_dynamics`).

Hydrate resolved copies:

```bash
uv run python scripts/z_generate_manuscript_variables.py
```

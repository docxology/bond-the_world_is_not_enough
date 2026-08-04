# Pandoc / Cross-reference Syntax (ELEKTRA)

This manuscript uses Pandoc + pandoc-crossref. The heavy lifting (numbering,
captions, token hydration) is handled by the rendering toolchain; this file
documents the in-prose conventions only.

## {{TOKEN}} variables

Numeric and mission values are never hand-authored. Every value flows through
`src/the_world_is_not_enough/manuscript_variables.py::generate_variables()`
from `manuscript/config.yaml` plus measured model outputs. Reference them in a
numbered section as `{{TOKEN_NAME}}`. The live cross-reference test
(`tests/test_manuscript_variables.py`) fails if any `{{TOKEN}}` in a numbered
section is not generated.

Adding a token: add a key to `generate_variables()` (or `_config_tokens` /
`_run_domain_tokens`), use it in prose, and the cross-reference test guards
completeness.

## Figures

Refer to figures with pandoc-crossref labels, never hardcoded numbers:

```markdown
![Caption text](../output/figures/pipeline_network.png){#fig:pipeline_network}
```

Then cite in prose as `@fig:pipeline_network` (narrative) or
`[@fig:pipeline_network]` (parenthetical).

| Label | Image |
|---|---|
| `{#fig:pipeline_network}` | `output/figures/pipeline_network.png` |
| `{#fig:submarine_detection}` | `output/figures/submarine_detection.png` |
| `{#fig:hostage_dynamics}` | `output/figures/hostage_dynamics.png` |

## Citations

Use `@citekey` in prose with a matching `references.bib` entry, e.g.
`@edmonds_karp`, `@ford_fulkerson`, `@brandes`, `@dijkstra`, `@urick`,
`@namnyak`, `@de_fabrique`.

## Math

LaTeX math via `$...$` (inline) and `$$...$$` (display). Keep display math
self-contained; the rendering pipeline wraps sections appropriately.

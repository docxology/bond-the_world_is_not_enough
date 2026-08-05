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

| Label | Image | Pillar |
|---|---|---|
| `{#fig:pipeline_network}` | `output/figures/pipeline_network.png` | §3.1 pipeline security |
| `{#fig:submarine_detection}` | `output/figures/submarine_detection.png` | §3.2 submarine evasion |
| `{#fig:hostage_dynamics}` | `output/figures/hostage_dynamics.png` | §3.3 hostage psychology |
| `{#fig:sensor_fusion_track}` | `output/figures/sensor_fusion_track.png` | §3.6 sensor fusion |

## Citations

Use `@citekey` in prose with a matching `references.bib` entry:
`@ford_fulkerson`, `@edmonds_karp`, `@brandes`, `@dijkstra` (flow and
routing); `@urick` (passive sonar); `@namnyak`, `@de_fabrique` (hostage
psychology); `@stott`, `@dobson_op` (power systems); `@rubinstein`
(bargaining); `@kalman` (state estimation).

## Math

LaTeX math via `$...$` (inline) and `$$...$$` (display). Keep display math
self-contained; the rendering pipeline wraps sections appropriately.

**Escape exactly once.** Markdown source is not a Python string literal: write
`$\theta$`, `\quad`, `\hat{x}` with a *single* backslash. A doubled `\\`
inside inline math is a LaTeX line break, and silently renders as a broken
formula rather than the intended symbol — this was a real defect in §2.4–2.6.
The only legitimate `\\` is the row separator inside an `aligned` block.

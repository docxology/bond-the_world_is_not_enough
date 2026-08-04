# COUNTS — the_world_is_not_enough (ELEKTRA)

Live, generated counts for this package (recompute on meaningful changes; do
not let prose drift from them).

| Metric | Value |
| --- | --- |
| Test count (pytest) | 148 |
| Line + branch coverage on `src/` | 97.18% (gate: ≥90%) |
| Coverage gate | `uv run pytest tests/ --cov=src --cov-fail-under=90` |
| Domain modules | 3 (`pipeline_security`, `sub_defense`, `hostage_psychology`) |
| MissionProvider stages | 5 (brief, recon, plan, execute, debrief) |
| Concept figures | 3 |
| Manuscript sections | 8 (00–07) + references |

## Regenerate

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90 -q | tail -1
```

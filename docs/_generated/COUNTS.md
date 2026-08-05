# COUNTS — the_world_is_not_enough (ELEKTRA)

Live, generated counts for this package (recompute on meaningful changes; do
not let prose drift from them).

| Metric | Value |
| --- | --- |
| Test count (pytest) | 230 |
| Line + branch coverage on `src/` | 97.15% (gate: ≥90%) |
| Coverage gate | `uv run pytest tests/ --cov=src --cov-fail-under=90` |
| Domain modules | 6 (`pipeline_security`, `sub_defense`, `hostage_psychology`, `power_grid`, `negotiation_tactics`, `sensor_fusion`) |
| MissionProvider stages | 5 (brief, recon, plan, execute, debrief) |
| Mission plan steps | 8 |
| Concept figures | 4 |
| Manuscript sections | 8 (00–07) + references |

## Regenerate

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90 -q | tail -1
```

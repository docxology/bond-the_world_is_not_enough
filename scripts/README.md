# scripts/ — the_world_is_not_enough (ELEKTRA)

Thin per-mission-phase orchestrators. Business logic lives in `src/`; these
scripts bootstrap `src/` onto `sys.path`, load the provider or call the
figure/token generators, and print canonical output.

| Script | Mission phase / action |
| --- | --- |
| `brief.py` | Print the frozen `MissionBrief` as BOND-API JSON |
| `recon.py` | Run reconnaissance, print `ReconReport` JSON |
| `plan.py` | Print the `MissionPlan` JSON |
| `execute.py` | Execute the mission, print `MissionOutcome` JSON, persist provenance |
| `debrief.py` | Print the `Debrief` (outcome + lessons) JSON |
| `generate_figures.py` | Render the three deterministic concept figures |
| `z_generate_manuscript_variables.py` | Hydrate manuscript `{{TOKEN}}`s (strict by default; `--allow-draft` relaxes) |

## Conventions

- Each script is runnable as `uv run python scripts/<name>.py` (it inserts
  `src/` into `sys.path` itself).
- Deterministic output; no wall-clock in the printed payloads (persisted
  records use a fixed mission epoch).
- Exit code `0` on success. `execute.py` writes
  `output/data/elektra_mission.json` via
  `bond_utilities.mission_io.record_provenance_outcome`.

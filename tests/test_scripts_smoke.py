"""Subprocess smoke tests for the ELEKTRA phase CLIs and artifact scripts.

Each phase script must exit 0 and emit canonical BOND-API JSON; the figure and
manuscript-variable scripts must produce their artifacts. Real subprocesses,
no mocks.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_script(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def json_output(name: str) -> dict:
    proc = run_script(name)
    assert proc.returncode == 0, f"{name} failed: {proc.stderr}"
    return json.loads(proc.stdout)


class TestPhaseScripts:
    def test_brief(self) -> None:
        data = json_output("brief.py")
        assert data.get("__bond_type__") == "MissionBrief"
        assert data["codename"] == "ELEKTRA"

    def test_recon(self) -> None:
        data = json_output("recon.py")
        assert data.get("__bond_type__") == "ReconReport"
        assert data["findings"]["__bond_type__"] == "tuple"

    def test_plan(self) -> None:
        data = json_output("plan.py")
        assert data.get("__bond_type__") == "MissionPlan"

    def test_execute(self) -> None:
        data = json_output("execute.py")
        assert data.get("__bond_type__") == "MissionOutcome"
        assert data["success"] is True
        assert data["results"]["choke_point_count"] == 1

    def test_debrief(self) -> None:
        data = json_output("debrief.py")
        assert data.get("__bond_type__") == "Debrief"
        assert data["lessons"]["__bond_type__"] == "tuple"


class TestFigureScript:
    def test_generates_all_figure_pngs(self, tmp_path: Path) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_figures.py"),
                "--output-dir",
                str(tmp_path),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        for name in (
            "pipeline_network.png",
            "submarine_detection.png",
            "hostage_dynamics.png",
            "sensor_fusion_track.png",
        ):
            assert (tmp_path / name).is_file(), f"missing {name}: {proc.stdout}"


class TestManuscriptVariableScript:
    def test_writes_json_and_tree(self, tmp_path: Path) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "z_generate_manuscript_variables.py"),
                "--output-dir",
                str(tmp_path),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        variables = json.loads(
            (tmp_path / "data" / "manuscript_variables.json").read_text(
                encoding="utf-8"
            )
        )
        assert variables["MISSION_CODENAME"] == "ELEKTRA"
        # resolved tree written (sections exist under output/manuscript)
        sections = list((tmp_path / "manuscript").glob("[0-9][0-9]_*.md"))
        assert len(sections) >= 3


class TestExecutePersistence:
    def test_writes_provenance_record(self, tmp_path: Path) -> None:
        # execute.py writes to <package>/output/data by default; the tmp_path
        # is kept so the record is exercised through the real script's default.
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "execute.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        default_record = ROOT / "output" / "data" / "elektra_mission.json"
        assert default_record.is_file()
        record = json.loads(default_record.read_text(encoding="utf-8"))
        assert record["mission_id"] == "the_world_is_not_enough"
        assert record["codename"] == "ELEKTRA"
        assert "input_hash" in record["provenance"]
        assert record["provenance"]["seed"] == 1999

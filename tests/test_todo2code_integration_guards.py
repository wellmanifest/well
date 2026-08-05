from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _run_intent(project: Path, output: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "wellmanifest",
            "intent",
            "analyze",
            str(project),
            "-o",
            str(output),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_project(tmp_path: Path, *, schema_ref: str = "schema.json", first_path: str = "a.json") -> Path:
    (tmp_path / "schema.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "a.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "b.json").write_text("{}\n", encoding="utf-8")
    project_file = tmp_path / "project.json"
    project_file.write_text(
        json.dumps(
            {
                "schema": "wellm.intent-format-project/v1",
                "id": "guard-test",
                "schemaRef": schema_ref,
                "representations": [
                    {"id": "a", "path": first_path, "dialect": "json"},
                    {"id": "b", "path": "b.json", "dialect": "json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    return project_file


@pytest.mark.parametrize("member", ["schemaRef", "representation"])
def test_intent_project_rejects_paths_outside_project(tmp_path: Path, member: str) -> None:
    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    project_file = _write_project(
        tmp_path,
        schema_ref="../outside.json" if member == "schemaRef" else "schema.json",
        first_path="../outside.json" if member == "representation" else "a.json",
    )

    result = _run_intent(project_file, tmp_path / "report.json")

    assert result.returncode != 0
    assert "project directory" in result.stderr


def test_intent_project_rejects_duplicate_representation_ids(tmp_path: Path) -> None:
    project_file = _write_project(tmp_path)
    payload = json.loads(project_file.read_text(encoding="utf-8"))
    payload["representations"][1]["id"] = "a"
    project_file.write_text(json.dumps(payload), encoding="utf-8")

    result = _run_intent(project_file, tmp_path / "report.json")

    assert result.returncode != 0
    assert "ids must be unique" in result.stderr


def test_intent_project_requires_two_representations(tmp_path: Path) -> None:
    project_file = _write_project(tmp_path)
    payload = json.loads(project_file.read_text(encoding="utf-8"))
    payload["representations"] = payload["representations"][:1]
    project_file.write_text(json.dumps(payload), encoding="utf-8")

    result = _run_intent(project_file, tmp_path / "report.json")

    assert result.returncode != 0
    assert "at least two representations" in result.stderr

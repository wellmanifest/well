#!/usr/bin/env python3
"""Verify that Python and JavaScript emit the same canonical Plesk plan."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from wellmanifest.plesk import PleskPublicationPlanner, WorkspaceResolver, load_project_registry


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/plesk/site/www"
REFERENCE = "workspace:obslugabiurowa-pl"


def python_plan() -> dict[str, object]:
    registry = load_project_registry(ROOT / "examples/plesk/projects.json")
    planner = PleskPublicationPlanner(
        registry,
        WorkspaceResolver(mappings={REFERENCE: SOURCE}, workspace_root=ROOT),
    )
    return planner.build("obslugabiurowa-pl").model_dump(mode="json", by_alias=True)


def javascript_plan() -> dict[str, object]:
    source = r"""
import fs from "node:fs";
import {buildPleskPublicationPlan} from "./packages/js/src/index.js";
const registry = JSON.parse(fs.readFileSync("./examples/plesk/projects.json", "utf8"));
const plan = await buildPleskPublicationPlan(registry, {
  projectId: "obslugabiurowa-pl",
  sourceRefs: {"workspace:obslugabiurowa-pl": process.env.WELLM_SOURCE_DIR},
});
process.stdout.write(JSON.stringify(plan));
"""
    environment = {**os.environ, "WELLM_SOURCE_DIR": str(SOURCE)}
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", source],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def canonical(value: dict[str, object]) -> dict[str, object]:
    normalized = dict(value)
    normalized.pop("created_at", None)
    normalized.pop("manifest_hash", None)
    return normalized


def main() -> None:
    py_plan = python_plan()
    js_plan = javascript_plan()
    assert py_plan["manifest_hash"] == js_plan["manifest_hash"]
    assert canonical(py_plan) == canonical(js_plan)
    print("Python/JavaScript Plesk plan parity: PASS")


if __name__ == "__main__":
    main()

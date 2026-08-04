from __future__ import annotations

import json
from pathlib import Path

from wellmanifest.situation import evaluate_situation_profile

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "situation-profile"


def test_situation_profile_evaluates_metrics_assessments_and_candidates() -> None:
    profile = json.loads((EXAMPLE / "public-site.capability-inventory.json").read_text())
    snapshots = json.loads((EXAMPLE / "inventory.json").read_text())
    result = evaluate_situation_profile(profile, snapshots)
    assert result["metrics"]["availability_ratio"] == 1.0
    assert result["assessments"]["bootstrap_playbook_ready"] == "ready"
    assert result["decision_candidates"][0]["id"] == "run_public_site_bootstrap"
    assert "objects" not in result

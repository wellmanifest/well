from __future__ import annotations

from pathlib import Path

from wellmanifest.runtime import WellManifestRuntime

ROOT = Path(__file__).resolve().parents[1]


def test_policy_dialect_parses_example_rules() -> None:
    runtime = WellManifestRuntime()
    source = (ROOT / "examples" / "policy" / "CONTRIBUTING.policy").read_text()
    document = runtime.parse(source, dialect="policy")
    ids = [rule["id"] for rule in document.ir["rules"]]
    assert ids == ["C-CONTEXT-001", "C-CONTEXT-002"]
    assert document.ir["rules"][0]["actions"][0]["verb"] == "SET"
    assert "BLOCKED" in document.ir["states"]


def test_original_contributing_markdown_is_importable_as_policy_ir() -> None:
    runtime = WellManifestRuntime()
    source = (ROOT / "tests" / "fixtures" / "governance" / "CONTRIBUTING.md").read_text()
    document = runtime.parse(source, dialect="policy")
    assert len(document.ir["rules"]) >= 40
    assert any(rule["id"] == "C-VALIDATION-006" for rule in document.ir["rules"])
    assert any(item["from"] == "START" and item["to"] == "ANALYSIS" for item in document.ir["transitions"])

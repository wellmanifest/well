from __future__ import annotations

from pathlib import Path

from wellmanifest.intent_analysis import analyze_inline_representations, analyze_intent_project, todo2code_evidence
from wellmanifest.runtime import WellManifestRuntime

ROOT = Path(__file__).resolve().parents[1]


def test_multi_format_intent_is_equivalent_and_schema_valid() -> None:
    runtime = WellManifestRuntime()
    report = analyze_intent_project(runtime, ROOT / "examples" / "todo2code" / "intent-formats.wellm.yaml")
    assert report.equivalent
    assert len(report.representations) == 6
    assert len(report.pairs) == 15
    assert all(item.schema_valid is True for item in report.representations)
    evidence = todo2code_evidence(report)
    assert evidence["schema"] == "wellm.todo2code-format-evidence/v1"
    assert evidence["todo2code"]["epistemicClass"] == "fact"
    assert evidence["todo2code"]["confidence"] == 1.0


def test_multi_format_intent_reports_semantic_drift() -> None:
    runtime = WellManifestRuntime()
    base = ROOT / "examples" / "todo2code"
    report = analyze_inline_representations(
        runtime,
        {
            "id": "drift",
            "representations": [
                {"id": "json", "dialect": "json", "sourceName": "intent.json", "source": (base / "intent.json").read_text()},
                {"id": "yaml", "dialect": "yaml", "sourceName": "intent-drift.yaml", "source": (base / "intent-drift.yaml").read_text()},
            ],
        },
    )
    assert not report.equivalent
    assert report.pairs[0].change_count > 0
    assert any(item.code == "WM-INTENT-DRIFT-001" for item in report.diagnostics)

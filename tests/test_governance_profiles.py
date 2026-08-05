from __future__ import annotations

import json
import shutil
from pathlib import Path

from wellmanifest.governance import (
    GovernanceBuilder,
    roundtrip_document,
    semantic_diff,
    semantic_sha256,
    serialize_profile,
)
from wellmanifest.models import ValidationRequest
from wellmanifest.runtime import WellManifestRuntime

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "tests" / "fixtures" / "governance-current"
LEGACY = ROOT / "tests" / "fixtures" / "governance-legacy"


def test_repo_json_profile_orders_schema_properties_and_dynamic_keys() -> None:
    value = {
        "coordination": {"workstreams": {"zeta": {"ownedPaths": ["z/**"]}, "alpha": {"ownedPaths": ["a/**"]}}},
        "standard": {"version": "1.0.0", "id": "example"},
        "schema": "demo/v1",
    }
    schema = {
        "type": "object",
        "properties": {
            "schema": {"type": "string"},
            "standard": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "version": {"type": "string"}},
            },
            "coordination": {
                "type": "object",
                "properties": {
                    "workstreams": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {"ownedPaths": {"type": "array", "items": {"type": "string"}}},
                        },
                    }
                },
            },
        },
    }
    rendered = serialize_profile(value, "repo-json@1", schema=schema)
    assert rendered.index('"schema"') < rendered.index('"standard"') < rendered.index('"coordination"')
    assert rendered.index('"id"') < rendered.index('"version"')
    assert rendered.index('"alpha"') < rendered.index('"zeta"')
    assert rendered.endswith("\n")


def test_semantic_digest_ignores_key_order_and_integral_float_spelling() -> None:
    left = {"b": 2, "a": {"value": 1.0}}
    right = {"a": {"value": 1}, "b": 2}
    assert semantic_sha256(left) == semantic_sha256(right)


def test_governance_builder_build_check_and_drift(tmp_path: Path) -> None:
    source = ROOT / "examples" / "governance"
    project = tmp_path / "governance"
    shutil.copytree(source, project)
    builder = GovernanceBuilder(WellManifestRuntime())

    first = builder.build(project / "wellm.project.yaml")
    assert first.ok
    assert all(item.status == "CURRENT" for item in first.artifacts)

    checked = builder.build(project / "wellm.project.yaml", check=True)
    assert checked.ok
    assert all(item.status == "CURRENT" for item in checked.artifacts)

    target = project / "generated" / "intent.json"
    target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")
    drift = builder.build(project / "wellm.project.yaml", check=True)
    assert not drift.ok
    assert any(item.id == "ticket-intent" and item.status == "DRIFT" for item in drift.artifacts)
    assert any(item.code == "WM-GOV-102" for item in drift.diagnostics)


def test_schema_error_points_to_typed_source_line() -> None:
    source = '''#@wellmanifest kind="data"
schema = "new-project.intent/v2"
ticket = "wrong"
summary = "x"
workstream = "integration"
allowedPaths = ["README.md"]
forbiddenPaths = []
stacks = []
dependsOn = []
conflictsWith = []
integrationTicket = null
'''
    schema = json.loads((CURRENT / "intent.schema.json").read_text(encoding="utf-8"))
    response = WellManifestRuntime().validate(
        ValidationRequest(source=source, dialect="typed", schema=schema, source_name="intent.wm")
    )
    diagnostic = next(item for item in response.diagnostics if item.path == "/ticket")
    assert diagnostic.range is not None
    assert diagnostic.range.start.line == 3


def test_semantic_diff_exposes_governance_contract_drift() -> None:
    current = json.loads((CURRENT / "manifest.default.json").read_text(encoding="utf-8"))
    legacy = json.loads((LEGACY / "manifest.default.json").read_text(encoding="utf-8"))
    report = semantic_diff(current, legacy)
    assert not report.equivalent
    assert any(change.path == "/approvalEvidence" and change.operation == "remove" for change in report.changes)
    assert any(
        change.path == "/trustedApprovalSources"
        and change.operation == "remove"
        and change.before == "github-app-review"
        for change in report.changes
    )

    current_diagnostics = json.loads((CURRENT / "diagnostics.json").read_text(encoding="utf-8"))
    legacy_diagnostics = json.loads((LEGACY / "diagnostics.json").read_text(encoding="utf-8"))
    diagnostic_report = semantic_diff(current_diagnostics, legacy_diagnostics)
    removed = {change.path for change in diagnostic_report.changes if change.operation == "remove"}
    assert "/codes/GOV-APPROVAL-003" in removed
    assert "/codes/GOV-APPROVAL-005" in removed


def test_roundtrip_json_yaml_typescript_preserves_semantics() -> None:
    runtime = WellManifestRuntime()
    source = (CURRENT / "manifest.default.json").read_text(encoding="utf-8")
    document = runtime.parse(source, dialect="json", source_name="manifest.default.json")
    schema = json.loads((CURRENT / "manifest.schema.json").read_text(encoding="utf-8"))
    report = roundtrip_document(runtime, document, ["yaml", "typescript", "json"], schema=schema)
    assert report.equivalent
    assert all(step.equivalent_to_source for step in report.steps)


def test_approval_evidence_schema_conditional_branches_are_enforced() -> None:
    runtime = WellManifestRuntime()
    schema = json.loads((CURRENT / "approval-evidence.schema.json").read_text(encoding="utf-8"))
    base = {
        "schema": "new-project.approval-evidence/v1",
        "repository": "wellmanifest/new-project",
        "pullRequest": 1,
        "headSha": "a" * 40,
        "ticket": "ticket-002",
    }
    invalid_app = {
        **base,
        "source": "github-app-review",
        "actor": {"login": "validator", "type": "User"},
        "verification": {"method": "github-api-allowlist", "verified": True},
    }
    response = runtime.validate(ValidationRequest(source=invalid_app, dialect="json", schema=schema))
    assert not response.valid

    invalid_attestation = {
        **base,
        "source": "signed-attestation",
        "actor": {"login": "workflow", "type": "Workflow"},
        "verification": {"method": "sigstore", "verified": True},
    }
    response = runtime.validate(ValidationRequest(source=invalid_attestation, dialect="json", schema=schema))
    assert not response.valid


def test_json_parser_rejects_duplicate_keys() -> None:
    runtime = WellManifestRuntime()
    try:
        runtime.parse('{"a": 1, "a": 2}', dialect="json")
    except ValueError as exc:
        assert "Duplicate JSON key" in str(exc)
    else:
        raise AssertionError("duplicate JSON key was accepted")

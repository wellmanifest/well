from __future__ import annotations

import json
from pathlib import Path

from wellmanifest.models import ValidationRequest
from wellmanifest.runtime import WellManifestRuntime

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "governance"


def test_existing_intent_is_valid_against_uploaded_schema() -> None:
    runtime = WellManifestRuntime()
    intent = json.loads((FIXTURES / "intent.json").read_text())
    schema = json.loads((FIXTURES / "intent.schema.json").read_text())
    response = runtime.validate(ValidationRequest(source=intent, dialect="json", schema=schema))
    assert response.valid


def test_schema_validation_reports_stable_error_shape() -> None:
    runtime = WellManifestRuntime()
    schema = json.loads((FIXTURES / "intent.schema.json").read_text())
    invalid = {"schema": "new-project.intent/v2", "ticket": "wrong"}
    response = runtime.validate(ValidationRequest(source=invalid, dialect="json", schema=schema))
    assert not response.valid
    assert any(item.code == "WM-SCHEMA-100" for item in response.diagnostics)
    assert any(item.path == "/ticket" for item in response.diagnostics)


def test_existing_manifest_is_valid() -> None:
    runtime = WellManifestRuntime()
    manifest = json.loads((FIXTURES / "manifest.default.json").read_text())
    schema = json.loads((FIXTURES / "manifest.schema.json").read_text())
    response = runtime.validate(ValidationRequest(source=manifest, dialect="json", schema=schema))
    assert response.valid

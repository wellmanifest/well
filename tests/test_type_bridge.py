from __future__ import annotations

import json
from pathlib import Path

from wellmanifest.models import ConversionRequest
from wellmanifest.runtime import WellManifestRuntime
from wellmanifest.type_bridge import (
    json_schema_to_python,
    json_schema_to_typed_module,
    json_schema_to_typescript,
    typed_module_to_json_schema,
)

ROOT = Path(__file__).resolve().parents[1]


def test_json_schema_typed_module_roundtrip_is_exact() -> None:
    schema = json.loads((ROOT / "schemas" / "status.schema.json").read_text(encoding="utf-8"))
    module = json_schema_to_typed_module(schema)
    restored = typed_module_to_json_schema(module, source_name="status.schema.wm")
    assert restored == schema
    assert "wellm.type-module/v1" in module


def test_complex_governance_schemas_roundtrip_without_losing_conditionals_or_tuples() -> None:
    for name in ("approval-evidence.schema.json", "manifest.schema.json", "intent.schema.json"):
        schema = json.loads((ROOT / "examples" / "governance" / "fixtures" / name).read_text(encoding="utf-8"))
        module = json_schema_to_typed_module(schema)
        restored = typed_module_to_json_schema(module, source_name=name + ".wm")
        assert restored == schema


def test_schema_driven_data_to_typed_adds_field_types() -> None:
    runtime = WellManifestRuntime()
    schema = json.loads((ROOT / "examples" / "todo2code" / "intent.schema.json").read_text(encoding="utf-8"))
    source = (ROOT / "examples" / "todo2code" / "intent.json").read_text(encoding="utf-8")
    result = runtime.convert(
        ConversionRequest(
            source=source,
            source_dialect="json",
            target_dialect="typed",
            schema_document=schema,
            type_mode="schema",
        )
    )
    assert result.output is not None
    assert not any(item.severity.value == "ERROR" for item in result.diagnostics)
    assert 'data ticket: String = "ticket-002"' in (result.output or "")
    assert "data integrationTicket: Null | String = null" in (result.output or "")


def test_schema_codegen_produces_typescript_and_importable_python() -> None:
    schema = json.loads((ROOT / "schemas" / "status.schema.json").read_text(encoding="utf-8"))
    ts = json_schema_to_typescript(schema, root_name="StatusDocument")
    py = json_schema_to_python(schema, root_name="StatusDocument")
    assert "export type StatusDocument" in ts
    assert "class StatusDocument(TypedDict):" in py
    compile(py, "generated_status_types.py", "exec")

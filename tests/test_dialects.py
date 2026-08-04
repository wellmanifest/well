from __future__ import annotations

import json
from pathlib import Path

from wellmanifest.models import ConversionRequest, Severity
from wellmanifest.runtime import WellManifestRuntime

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "dialects"
EXPECTED = {
    "status": {
        "operation": "002-cv-pdf2md",
        "value": "SUCCEEDED",
        "errors": [],
    }
}


def test_four_status_syntaxes_normalize_to_one_data_model() -> None:
    runtime = WellManifestRuntime()
    cases = [
        ("status.hcl", "hcl"),
        ("status-split.wm", "typed"),
        ("status-inline.wm", "typed"),
        ("status-comment.hcl", "hcl"),
    ]
    for filename, dialect in cases:
        document = runtime.parse((EXAMPLES / filename).read_text(), dialect=dialect, source_name=filename)
        assert document.data == EXPECTED


def test_split_and_inline_annotations_produce_type_metadata() -> None:
    runtime = WellManifestRuntime()
    split = runtime.parse((EXAMPLES / "status-split.wm").read_text(), dialect="typed")
    inline = runtime.parse((EXAMPLES / "status-inline.wm").read_text(), dialect="typed")
    assert split.metadata.type_hints["/status/operation"] == "FolderOperationId"
    assert inline.metadata.type_hints["/status/errors"] == "[OperationError]"
    assert any(item.code == "WM-TYPE-101" for item in split.diagnostics)


def test_comment_type_hint_is_warning_not_normative_error() -> None:
    runtime = WellManifestRuntime()
    document = runtime.parse((EXAMPLES / "status-comment.hcl").read_text(), dialect="hcl")
    assert any(item.code == "WM-TYPE-102" and item.severity == Severity.WARNING for item in document.diagnostics)
    assert document.ok


def test_json_yaml_toml_roundtrip() -> None:
    runtime = WellManifestRuntime()
    source = (EXAMPLES / "status.json").read_text()
    yaml_result = runtime.convert(ConversionRequest(source=source, source_dialect="json", target_dialect="yaml"))
    assert yaml_result.output and "operation: 002-cv-pdf2md" in yaml_result.output
    toml_result = runtime.convert(
        ConversionRequest(source=yaml_result.output, source_dialect="yaml", target_dialect="toml")
    )
    assert toml_result.output and "[status]" in toml_result.output
    json_result = runtime.convert(
        ConversionRequest(source=toml_result.output, source_dialect="toml", target_dialect="json")
    )
    assert json.loads(json_result.output) == EXPECTED


def test_typed_module_keeps_declarations_and_data() -> None:
    runtime = WellManifestRuntime()
    document = runtime.parse((EXAMPLES / "status.wm").read_text(), dialect="typed")
    assert document.data == EXPECTED
    assert document.ir["declarations"][0]["kind"] == "type"
    assert document.metadata.type_hints["/status"] == "OperationStatus"


def test_proto3_import_exposes_messages_services_and_field_numbers() -> None:
    runtime = WellManifestRuntime()
    source = (ROOT / "examples" / "proto" / "register.proto").read_text()
    document = runtime.parse(source, dialect="proto3")
    assert document.ir["syntax"] == "proto3"
    assert document.ir["messages"][0]["fields"][0] == {
        "label": None,
        "type": "int64",
        "name": "id",
        "number": 1,
    }
    assert document.ir["services"][0]["rpcs"][0]["name"] == "RegisterUser"

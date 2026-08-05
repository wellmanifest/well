from __future__ import annotations

from pathlib import Path

from wellmanifest.models import ConversionRequest
from wellmanifest.runtime import WellManifestRuntime

ROOT = Path(__file__).resolve().parents[1]


def test_simple_toon_is_json_compatible_and_roundtrips() -> None:
    runtime = WellManifestRuntime()
    source = (ROOT / "examples" / "todo2code" / "intent.toon.yaml").read_text(encoding="utf-8")
    document = runtime.parse(source, dialect="toon", source_name="intent.toon.yaml")
    assert document.metadata.source_dialect == "toon@1"
    assert document.metadata.directives["producer"] == "wellm"
    assert document.data["ticket"] == "ticket-002"
    result = runtime.convert(
        ConversionRequest(source=source, source_dialect="toon", target_dialect="json")
    )
    assert result.output is not None
    assert not any(item.severity.value == "ERROR" for item in result.diagnostics)
    assert '"ticket": "ticket-002"' in (result.output or "")


def test_real_code2llm_map_toon_imports_all_modules() -> None:
    runtime = WellManifestRuntime()
    path = ROOT / "examples" / "toon" / "map.toon.yaml"
    document = runtime.parse(path.read_text(encoding="utf-8"), dialect="toon", source_name=path.name)
    assert document.ir["kind"] == "code2llm-structural-map"
    assert document.data["schema"] == "code2llm.structural-map/v1"
    assert document.data["moduleCount"] == 235
    assert len(document.data["modules"]) == 235
    assert len(document.data["details"]) == 235
    assert "imports" in document.data["details"]["src/cli.ts"]["relations"]

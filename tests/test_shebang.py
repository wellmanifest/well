from __future__ import annotations

from pathlib import Path

from wellmanifest.runtime import WellManifestRuntime

ROOT = Path(__file__).resolve().parents[1]


def test_typed_shebang_is_preserved_as_runtime_metadata() -> None:
    source = (ROOT / "examples/shebang/status.wm").read_text(encoding="utf-8")
    document = WellManifestRuntime().parse(source, dialect="typed", source_name="status.wm")
    assert document.data["status"]["value"] == "SUCCEEDED"
    assert document.metadata.directives["shebang"] == "#!/usr/bin/env wellmanifest-typed"


def test_policy_shebang_selects_policy_without_shell_execution() -> None:
    source = (ROOT / "examples/shebang/policy.wmpolicy").read_text(encoding="utf-8")
    document = WellManifestRuntime().parse(source, dialect="policy", source_name="policy.wmpolicy")
    assert document.ir["rules"][0]["id"] == "C-CONTEXT-001"

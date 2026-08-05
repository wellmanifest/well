from __future__ import annotations


def test_original_wellm_01_api_remains_available() -> None:
    from well import Runtime, greet, hello

    assert hello() == "hello from well"
    assert greet("Anna") == "Hello, Anna!"
    assert Runtime().capabilities()["protocol"] == "wellmanifest.protocol/v1"


def test_new_primary_namespace_exposes_the_runtime() -> None:
    from wellm import WellManifestRuntime, __version__

    assert __version__ == "0.2.0rc3"
    assert WellManifestRuntime().capabilities()["protocol"] == "wellmanifest.protocol/v1"


def test_wellm_namespace_exports_governance_api():
    from wellm import GovernanceBuilder, WellManifestRuntime, semantic_diff, semantic_sha256

    assert GovernanceBuilder is not None
    assert WellManifestRuntime is not None
    assert semantic_diff({"a": 1}, {"a": 1}).equivalent is True
    assert semantic_sha256({"b": 2, "a": 1}) == (
        "sha256:43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )

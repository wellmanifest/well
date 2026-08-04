from __future__ import annotations


def test_original_wellm_01_api_remains_available() -> None:
    from well import Runtime, greet, hello

    assert hello() == "hello from well"
    assert greet("Anna") == "Hello, Anna!"
    assert Runtime().capabilities()["protocol"] == "wellmanifest.protocol/v1"


def test_new_primary_namespace_exposes_the_runtime() -> None:
    from wellm import WellManifestRuntime, __version__

    assert __version__ == "0.2.0rc2"
    assert WellManifestRuntime().capabilities()["protocol"] == "wellmanifest.protocol/v1"

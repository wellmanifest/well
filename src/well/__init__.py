"""Compatibility module for the original ``wellm`` 0.1.x package API."""

from __future__ import annotations

from wellmanifest import WellManifestRuntime, __version__


def hello() -> str:
    return "hello from well"


def greet(name: str = "world") -> str:
    return f"Hello, {name}!"


Runtime = WellManifestRuntime

__all__ = ["hello", "greet", "Runtime", "WellManifestRuntime", "__version__"]

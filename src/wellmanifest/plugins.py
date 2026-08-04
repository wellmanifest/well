from __future__ import annotations

from importlib import metadata
from typing import Any

from .models import Diagnostic, Severity

DIALECT_ENTRYPOINT_GROUP = "wellmanifest.dialects"
PROCESS_ENTRYPOINT_GROUP = "wellmanifest.processes"


def load_entrypoint_plugins(runtime: Any) -> list[Diagnostic]:
    """Load explicitly installed WellManifest plugins.

    A dialect entry point must return a Dialect instance. A process entry point
    must be a callable receiving the runtime and registering concrete adapters.
    Plugin loading is opt-in at application startup; documents cannot install or
    activate packages by themselves.
    """
    diagnostics: list[Diagnostic] = []
    groups = metadata.entry_points()
    for entrypoint in groups.select(group=DIALECT_ENTRYPOINT_GROUP):
        try:
            runtime.registry.register(entrypoint.load()())
            diagnostics.append(
                Diagnostic(code="WM-PLUGIN-INFO", severity=Severity.INFO, message=f"Loaded dialect plugin {entrypoint.name}")
            )
        except Exception as exc:  # plugin boundary: preserve a structured failure
            diagnostics.append(
                Diagnostic(
                    code="WM-PLUGIN-001",
                    severity=Severity.ERROR,
                    message=f"Dialect plugin {entrypoint.name} failed: {exc}",
                )
            )
    for entrypoint in groups.select(group=PROCESS_ENTRYPOINT_GROUP):
        try:
            entrypoint.load()(runtime)
            diagnostics.append(
                Diagnostic(code="WM-PLUGIN-INFO", severity=Severity.INFO, message=f"Loaded process plugin {entrypoint.name}")
            )
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    code="WM-PLUGIN-002",
                    severity=Severity.ERROR,
                    message=f"Process plugin {entrypoint.name} failed: {exc}",
                )
            )
    return diagnostics

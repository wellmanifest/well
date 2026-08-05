"""Primary Python namespace for the ``wellm`` distribution.

The implementation currently lives in :mod:`wellmanifest` so existing users can
upgrade without a flag day.  Public submodules are aliased under ``wellm``.
"""

from __future__ import annotations

import importlib
import sys

from wellmanifest import (
    Diagnostic,
    Document,
    Envelope,
    GovernanceBuilder,
    Severity,
    WellManifestRuntime,
    __version__,
    semantic_diff,
    semantic_sha256,
)

_PUBLIC_SUBMODULES = (
    "benchmark",
    "client",
    "models",
    "governance",
    "plesk",
    "urirun",
    "llmbench",
    "runtime",
    "schema",
    "security",
    "server",
    "versions",
    "type_bridge",
    "intent_analysis",
    "env_contract",
)

for _name in _PUBLIC_SUBMODULES:
    try:
        sys.modules[f"{__name__}.{_name}"] = importlib.import_module(f"wellmanifest.{_name}")
    except ModuleNotFoundError:
        # Optional modules are added by extras and may be absent in minimal builds.
        continue

__all__ = [
    "Diagnostic",
    "Document",
    "Envelope",
    "GovernanceBuilder",
    "Severity",
    "WellManifestRuntime",
    "semantic_diff",
    "semantic_sha256",
    "__version__",
]

from __future__ import annotations

import importlib
import importlib.util
from typing import Any

from wellmanifest.models import Diagnostic, Severity


def inspect_well_package() -> dict[str, Any]:
    """Report an installed `well` package without assuming an undocumented API."""
    if importlib.util.find_spec("well") is None:
        return {
            "available": False,
            "diagnostics": [
                Diagnostic(
                    code="WM-WELL-001",
                    severity=Severity.INFO,
                    message="Optional Python package `well` is not installed; WellManifest remains standalone.",
                ).model_dump(mode="json")
            ],
        }
    module = importlib.import_module("well")
    return {
        "available": True,
        "module": module.__name__,
        "version": getattr(module, "__version__", None),
        "diagnostics": [
            Diagnostic(
                code="WM-WELL-INFO",
                severity=Severity.INFO,
                message="The optional `well` module was detected; install an explicit adapter before invoking its API.",
            ).model_dump(mode="json")
        ],
    }

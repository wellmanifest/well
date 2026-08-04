from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, SchemaError

from .dialects.common import json_pointer
from .models import Diagnostic, Severity


class SchemaValidator:
    dialect = "json-schema@2020-12"

    def validate(self, instance: Any, schema: dict[str, Any], *, source: str | None = None) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            diagnostics.append(
                Diagnostic(
                    code="WM-SCHEMA-001",
                    severity=Severity.ERROR,
                    phase="schema",
                    message=f"Invalid JSON Schema 2020-12: {exc.message}",
                    source=source,
                    schema_path=json_pointer(list(exc.path)),
                )
            )
            return diagnostics

        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(instance), key=lambda item: (list(item.absolute_path), item.message))
        for error in errors:
            diagnostics.append(
                Diagnostic(
                    code="WM-SCHEMA-100",
                    severity=Severity.ERROR,
                    phase="validate",
                    message=error.message,
                    source=source,
                    path=json_pointer(list(error.absolute_path)),
                    schema_path=json_pointer(list(error.absolute_schema_path)),
                    details={"validator": error.validator, "validatorValue": error.validator_value},
                )
            )
        if not errors:
            diagnostics.append(
                Diagnostic(
                    code="WM-SCHEMA-200",
                    severity=Severity.INFO,
                    phase="validate",
                    message="Document conforms to JSON Schema 2020-12.",
                    source=source,
                )
            )
        return diagnostics

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .models import Document, DocumentMetadata


SCHEMA_DIALECT = "json-schema@2020-12"
TYPE_MODULE_SCHEMA = "wellm.type-module/v1"


def _escape_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _pascal(value: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", value)
    rendered = "".join(part[:1].upper() + part[1:] for part in parts if part)
    if not rendered:
        return "GeneratedType"
    if rendered[0].isdigit():
        rendered = "T" + rendered
    return rendered


def schema_name(schema: dict[str, Any], fallback: str = "Document") -> str:
    title = schema.get("title")
    if isinstance(title, str) and title.strip():
        return _pascal(title)
    schema_id = schema.get("$id")
    if isinstance(schema_id, str) and schema_id:
        stem = Path(schema_id.rsplit("/", 1)[-1]).stem.replace(".schema", "")
        if stem:
            return _pascal(stem)
    return _pascal(fallback)


def _resolve_ref(root: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return schema
    current: Any = root
    for raw in ref[2:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            return schema
        current = current[key]
    return current if isinstance(current, dict) else schema


def type_expression(schema: dict[str, Any], *, root: dict[str, Any] | None = None) -> str:
    root = root or schema
    if "$ref" in schema:
        ref = str(schema["$ref"])
        return _pascal(ref.rsplit("/", 1)[-1])
    if "const" in schema:
        return f"Literal<{json.dumps(schema['const'], ensure_ascii=False)}>"
    values = schema.get("enum")
    if isinstance(values, list) and values:
        return "Literal<" + " | ".join(json.dumps(item, ensure_ascii=False) for item in values) + ">"
    union = schema.get("oneOf") or schema.get("anyOf")
    if isinstance(union, list) and union:
        return " | ".join(type_expression(item, root=root) for item in union if isinstance(item, dict)) or "Any"
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return " | ".join(type_expression({"type": item}, root=root) for item in schema_type)
    if schema_type == "null":
        return "Null"
    if schema_type == "boolean":
        return "Bool"
    if schema_type == "integer":
        return "Int"
    if schema_type == "number":
        return "Number"
    if schema_type == "string":
        return "String"
    if schema_type == "array" or "prefixItems" in schema or "items" in schema:
        prefix = schema.get("prefixItems")
        if isinstance(prefix, list):
            return "[" + ", ".join(type_expression(item, root=root) for item in prefix if isinstance(item, dict)) + "]"
        items = schema.get("items", {})
        item_type = type_expression(items, root=root) if isinstance(items, dict) else "Any"
        return f"[{item_type}]"
    if schema_type == "object" or "properties" in schema or "additionalProperties" in schema:
        title = schema.get("title")
        if isinstance(title, str) and title:
            return _pascal(title)
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"Map<String, {type_expression(additional, root=root)}>"
        return "Map<String, Any>"
    resolved = _resolve_ref(root, schema)
    if resolved is not schema:
        return type_expression(resolved, root=root)
    return "Any"


def apply_schema_type_hints(document: Document, schema: dict[str, Any]) -> Document:
    """Attach JSON-Pointer type hints derived from a JSON Schema to a document."""

    Draft202012Validator.check_schema(schema)
    hints = dict(document.metadata.type_hints)

    def visit(value: Any, current_schema: dict[str, Any], path: str) -> None:
        resolved = _resolve_ref(schema, current_schema)
        union = resolved.get("oneOf") or resolved.get("anyOf")
        if isinstance(union, list):
            # Prefer a branch that validates the concrete value.
            selected = next(
                (
                    candidate
                    for candidate in union
                    if isinstance(candidate, dict) and Draft202012Validator(candidate).is_valid(value)
                ),
                None,
            )
            if isinstance(selected, dict):
                resolved = _resolve_ref(schema, selected)
        if isinstance(value, dict):
            properties = resolved.get("properties", {})
            additional = resolved.get("additionalProperties")
            for key, item in value.items():
                child_schema = properties.get(key) if isinstance(properties, dict) else None
                if not isinstance(child_schema, dict) and isinstance(additional, dict):
                    child_schema = additional
                if not isinstance(child_schema, dict):
                    child_schema = {}
                pointer = f"{path}/{_escape_pointer(str(key))}" if path else f"/{_escape_pointer(str(key))}"
                hints[pointer] = type_expression(child_schema, root=schema)
                visit(item, child_schema, pointer)
        elif isinstance(value, list):
            prefix = resolved.get("prefixItems")
            items = resolved.get("items")
            for index, item in enumerate(value):
                child_schema: dict[str, Any] = {}
                if isinstance(prefix, list) and index < len(prefix) and isinstance(prefix[index], dict):
                    child_schema = prefix[index]
                elif isinstance(items, dict):
                    child_schema = items
                pointer = f"{path}/{index}" if path else f"/{index}"
                hints[pointer] = type_expression(child_schema, root=schema)
                visit(item, child_schema, pointer)

    visit(document.data, schema, "")
    document.metadata.type_hints = hints
    document.metadata.schema_dialect = SCHEMA_DIALECT
    return document


def infer_type_hints(document: Document) -> Document:
    hints = dict(document.metadata.type_hints)

    def inferred(value: Any) -> str:
        if value is None:
            return "Null"
        if isinstance(value, bool):
            return "Bool"
        if isinstance(value, int):
            return "Int"
        if isinstance(value, float):
            return "Number"
        if isinstance(value, str):
            return "String"
        if isinstance(value, list):
            types = sorted({inferred(item) for item in value})
            return "[" + (" | ".join(types) if types else "Any") + "]"
        if isinstance(value, dict):
            return "Map<String, Any>"
        return "Any"

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                pointer = f"{path}/{_escape_pointer(str(key))}" if path else f"/{_escape_pointer(str(key))}"
                hints[pointer] = inferred(item)
                visit(item, pointer)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                pointer = f"{path}/{index}" if path else f"/{index}"
                hints[pointer] = inferred(item)
                visit(item, pointer)

    visit(document.data, "")
    document.metadata.type_hints = hints
    return document


def json_schema_to_typed_module(schema: dict[str, Any], *, root_name: str | None = None) -> str:
    """Encode a complete Draft 2020-12 schema as a typed Wellm module.

    The exact schema document remains the normative payload.  Human-readable
    type aliases can be generated independently without weakening round-trip
    fidelity.
    """

    Draft202012Validator.check_schema(schema)
    name = root_name or schema_name(schema)
    document = Document(
        metadata=DocumentMetadata(
            source_dialect="json@rfc8259",
            document_kind="schema",
            schema_dialect=SCHEMA_DIALECT,
            directives={"typeModule": TYPE_MODULE_SCHEMA, "rootType": name},
            type_hints={"/schema": "JSONSchema202012"},
        ),
        data={"schema": deepcopy(schema)},
        ir={"kind": "schema", "dialect": SCHEMA_DIALECT, "rootType": name, "schema": deepcopy(schema)},
    )
    from .dialects.structured import TypedDialect

    body = TypedDialect().emit(document, projection="data", pretty=True)
    return (
        "#!/usr/bin/env wellm-typed\n"
        f'#@wellmanifest kind="schema" schemaDialect="{SCHEMA_DIALECT}" '
        f'typeModule="{TYPE_MODULE_SCHEMA}" rootType="{name}"\n\n'
        + body
    )


def typed_module_to_json_schema(source: str, *, source_name: str | None = None) -> dict[str, Any]:
    from .dialects.structured import TypedDialect

    document = TypedDialect().parse(source, source_name=source_name)
    value = document.data.get("schema") if isinstance(document.data, dict) else None
    if not isinstance(value, dict):
        raise ValueError("Typed schema module must contain `data schema: JSONSchema202012 = { ... }`")
    Draft202012Validator.check_schema(value)
    return value


def _ts_property_name(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name) else json.dumps(name, ensure_ascii=False)


def _ts_type(schema: dict[str, Any], root: dict[str, Any]) -> str:
    if "$ref" in schema:
        return _pascal(str(schema["$ref"]).rsplit("/", 1)[-1])
    if "const" in schema:
        return json.dumps(schema["const"], ensure_ascii=False)
    if isinstance(schema.get("enum"), list):
        return " | ".join(json.dumps(value, ensure_ascii=False) for value in schema["enum"]) or "never"
    union = schema.get("oneOf") or schema.get("anyOf")
    if isinstance(union, list):
        return " | ".join(_ts_type(item, root) for item in union if isinstance(item, dict)) or "unknown"
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return " | ".join(_ts_type({"type": item}, root) for item in schema_type)
    if schema_type == "null":
        return "null"
    if schema_type == "boolean":
        return "boolean"
    if schema_type in {"integer", "number"}:
        return "number"
    if schema_type == "string":
        return "string"
    if schema_type == "array" or "prefixItems" in schema or "items" in schema:
        prefix = schema.get("prefixItems")
        if isinstance(prefix, list):
            return "readonly [" + ", ".join(_ts_type(item, root) for item in prefix if isinstance(item, dict)) + "]"
        items = schema.get("items", {})
        return f"readonly {_ts_type(items, root) if isinstance(items, dict) else 'unknown'}[]"
    if schema_type == "object" or "properties" in schema:
        required = set(schema.get("required", []))
        properties = schema.get("properties", {})
        fields = []
        if isinstance(properties, dict):
            for name, child in properties.items():
                if not isinstance(child, dict):
                    continue
                optional = "" if name in required else "?"
                fields.append(f"readonly {_ts_property_name(name)}{optional}: {_ts_type(child, root)};")
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            fields.append(f"readonly [key: string]: {_ts_type(additional, root)};")
        return "{ " + " ".join(fields) + " }"
    return "unknown"


def json_schema_to_typescript(schema: dict[str, Any], *, root_name: str | None = None) -> str:
    Draft202012Validator.check_schema(schema)
    name = root_name or schema_name(schema)
    lines = ["// Generated by wellm from JSON Schema 2020-12.", "// Do not edit generated declarations directly.", ""]
    defs = schema.get("$defs", {})
    if isinstance(defs, dict):
        for def_name, value in defs.items():
            if isinstance(value, dict):
                lines.append(f"export type {_pascal(def_name)} = {_ts_type(value, schema)};")
                lines.append("")
    lines.append(f"export type {name} = {_ts_type(schema, schema)};")
    return "\n".join(lines).rstrip() + "\n"


def _py_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return _pascal(str(schema["$ref"]).rsplit("/", 1)[-1])
    if "const" in schema:
        return f"Literal[{schema['const']!r}]"
    values = schema.get("enum")
    if isinstance(values, list):
        return "Literal[" + ", ".join(repr(value) for value in values) + "]"
    union = schema.get("oneOf") or schema.get("anyOf")
    if isinstance(union, list):
        return " | ".join(_py_type(item) for item in union if isinstance(item, dict)) or "Any"
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return " | ".join(_py_type({"type": item}) for item in schema_type)
    return {
        "null": "None",
        "boolean": "bool",
        "integer": "int",
        "number": "float",
        "string": "str",
    }.get(str(schema_type), "Any") if schema_type != "array" else f"list[{_py_type(schema.get('items', {}))}]"


def json_schema_to_python(schema: dict[str, Any], *, root_name: str | None = None) -> str:
    Draft202012Validator.check_schema(schema)
    name = root_name or schema_name(schema)
    lines = [
        "# Generated by wellm from JSON Schema 2020-12.",
        "from __future__ import annotations",
        "",
        "from typing import Any, Literal, NotRequired, TypedDict",
        "",
    ]

    def emit_type(type_name: str, value: dict[str, Any]) -> None:
        if value.get("type") == "object" or "properties" in value:
            required = set(value.get("required", []))
            lines.append(f"class {type_name}(TypedDict):")
            properties = value.get("properties", {})
            if not properties:
                lines.append("    pass")
            elif isinstance(properties, dict):
                for field, child in properties.items():
                    if not isinstance(child, dict):
                        continue
                    annotation = _py_type(child)
                    if field not in required:
                        annotation = f"NotRequired[{annotation}]"
                    safe_field = field if field.isidentifier() else None
                    if safe_field:
                        lines.append(f"    {safe_field}: {annotation}")
                    else:
                        lines.append(f"    # {field!r}: {annotation}  # non-identifier key")
            lines.append("")
        else:
            lines.append(f"{type_name} = {_py_type(value)}")
            lines.append("")

    defs = schema.get("$defs", {})
    if isinstance(defs, dict):
        for def_name, value in defs.items():
            if isinstance(value, dict):
                emit_type(_pascal(def_name), value)
    emit_type(name, schema)
    return "\n".join(lines).rstrip() + "\n"

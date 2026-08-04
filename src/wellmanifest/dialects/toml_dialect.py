from __future__ import annotations

import json
import tomllib
from typing import Any

from wellmanifest.models import Document, DocumentMetadata

from .base import Dialect
from .common import split_runtime_prelude
from .json_dialect import JsonDialect


class TomlDialect(Dialect):
    name = "toml@1.0"
    aliases = ("toml", "application/toml")
    media_types = ("application/toml",)
    extensions = (".toml", ".wm.toml")

    def parse(self, source: str, *, source_name: str | None = None) -> Document:
        cleaned, directives = split_runtime_prelude(source)
        data = tomllib.loads(cleaned)
        metadata = DocumentMetadata(
            source_dialect=self.name,
            document_kind=directives.get("kind", "data"),
            schema_ref=directives.get("schema"),
            schema_dialect="json-schema@2020-12" if directives.get("schema") else None,
            source_name=source_name,
            directives=directives,
        )
        return Document(metadata=metadata, data=data, ir={"kind": "data", "value": data}, source_text=source)

    def emit(self, document: Document, *, projection: str = "data", pretty: bool = True) -> str:
        value = document.data if projection == "data" else JsonDialect._ir_projection(document)
        if not isinstance(value, dict):
            raise ValueError("TOML root must be an object")
        lines: list[str] = []
        self._emit_table(value, (), lines)
        return "\n".join(lines).rstrip() + "\n"

    def _emit_table(self, mapping: dict[str, Any], path: tuple[str, ...], lines: list[str]) -> None:
        scalar_items: list[tuple[str, Any]] = []
        tables: list[tuple[str, dict[str, Any]]] = []
        array_tables: list[tuple[str, list[dict[str, Any]]]] = []
        for key, value in mapping.items():
            if isinstance(value, dict):
                tables.append((key, value))
            elif isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                array_tables.append((key, value))
            else:
                scalar_items.append((key, value))
        if path:
            lines.append(f"[{'.'.join(self._quote_key(part) for part in path)}]")
        for key, value in scalar_items:
            lines.append(f"{self._quote_key(key)} = {self._format_value(value)}")
        if scalar_items and (tables or array_tables):
            lines.append("")
        for index, (key, table) in enumerate(tables):
            self._emit_table(table, (*path, key), lines)
            if index < len(tables) - 1 or array_tables:
                lines.append("")
        for table_index, (key, rows) in enumerate(array_tables):
            for row_index, row in enumerate(rows):
                lines.append(f"[[{'.'.join(self._quote_key(part) for part in (*path, key))}]]")
                nested = {k: v for k, v in row.items() if isinstance(v, dict)}
                for row_key, row_value in row.items():
                    if not isinstance(row_value, dict):
                        lines.append(f"{self._quote_key(row_key)} = {self._format_value(row_value)}")
                for nested_key, nested_value in nested.items():
                    lines.append("")
                    self._emit_table(nested_value, (*path, key, nested_key), lines)
                if row_index < len(rows) - 1:
                    lines.append("")
            if table_index < len(array_tables) - 1:
                lines.append("")

    @staticmethod
    def _quote_key(key: str) -> str:
        return key if key.replace("_", "").replace("-", "").isalnum() else json.dumps(key, ensure_ascii=False)

    @classmethod
    def _format_value(cls, value: Any) -> str:
        if value is None:
            raise ValueError("TOML has no null value; conversion is lossy")
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, list):
            return "[" + ", ".join(cls._format_value(item) for item in value) + "]"
        raise ValueError(f"Unsupported TOML value: {type(value).__name__}")

    def probe(self, source: str, *, source_name: str | None = None) -> float:
        if source_name and source_name.lower().endswith(".toml"):
            return 0.9
        return 0.1 if "=" in source and "[" in source else 0.0

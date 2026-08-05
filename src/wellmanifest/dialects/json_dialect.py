from __future__ import annotations

import json
from typing import Any

from wellmanifest.models import Document, DocumentMetadata
from wellmanifest.source_maps import node_source_map

from .base import Dialect, DialectError
from .common import split_runtime_prelude


class _DuplicateKeyError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


class JsonDialect(Dialect):
    name = "json@rfc8259"
    aliases = ("json", "application/json", "application/wellmanifest+json")
    media_types = ("application/json", "application/wellmanifest+json")
    extensions = (".json", ".wm.json")

    def parse(self, source: str, *, source_name: str | None = None) -> Document:
        cleaned, directives = split_runtime_prelude(source)
        try:
            data: Any = json.loads(cleaned, object_pairs_hook=_strict_object)
        except _DuplicateKeyError as exc:
            raise DialectError("WM-JSON-101", str(exc)) from exc
        metadata = DocumentMetadata(
            source_dialect=self.name,
            document_kind=directives.get("kind", "data"),
            schema_ref=directives.get("schema"),
            schema_dialect="json-schema@2020-12" if directives.get("schema") else None,
            source_name=source_name,
            directives=directives,
        )
        return Document(
            metadata=metadata,
            data=data,
            ir={"kind": "data", "value": data},
            source_text=source,
            source_map=node_source_map(cleaned),
        )

    def emit(self, document: Document, *, projection: str = "data", pretty: bool = True) -> str:
        value = document.data if projection == "data" else self._ir_projection(document)
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
            allow_nan=False,
        ) + "\n"

    @staticmethod
    def _ir_projection(document: Document) -> dict[str, Any]:
        return {
            "$wellmanifest": document.metadata.model_dump(mode="json"),
            "data": document.data,
            "ir": document.ir,
            "sourceMap": {
                pointer: item.model_dump(mode="json") for pointer, item in document.source_map.items()
            },
            "diagnostics": [item.model_dump(mode="json") for item in document.diagnostics],
        }

    def probe(self, source: str, *, source_name: str | None = None) -> float:
        stripped = source.lstrip()
        if not stripped or stripped[0] not in "[{":
            return 0.0
        try:
            json.loads(stripped, object_pairs_hook=_strict_object)
            return 1.0
        except (json.JSONDecodeError, _DuplicateKeyError):
            return 0.1

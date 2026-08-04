from __future__ import annotations

import json
from typing import Any

from wellmanifest.models import Document, DocumentMetadata

from .base import Dialect
from .common import split_runtime_prelude


class JsonDialect(Dialect):
    name = "json@rfc8259"
    aliases = ("json", "application/json", "application/wellmanifest+json")
    media_types = ("application/json", "application/wellmanifest+json")
    extensions = (".json", ".wm.json")

    def parse(self, source: str, *, source_name: str | None = None) -> Document:
        cleaned, directives = split_runtime_prelude(source)
        data: Any = json.loads(cleaned)
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
        value = document.data if projection == "data" else self._ir_projection(document)
        return json.dumps(value, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":")) + "\n"

    @staticmethod
    def _ir_projection(document: Document) -> dict[str, Any]:
        return {
            "$wellmanifest": document.metadata.model_dump(mode="json"),
            "data": document.data,
            "ir": document.ir,
            "diagnostics": [item.model_dump(mode="json") for item in document.diagnostics],
        }

    def probe(self, source: str, *, source_name: str | None = None) -> float:
        stripped = source.lstrip()
        if not stripped or stripped[0] not in "[{":
            return 0.0
        try:
            json.loads(stripped)
            return 1.0
        except json.JSONDecodeError:
            return 0.1

from __future__ import annotations

import json
from typing import Any

import yaml

from wellmanifest.models import Document, DocumentMetadata

from .base import Dialect
from .common import split_runtime_prelude
from .json_dialect import JsonDialect


class _NoDuplicateSafeLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_NoDuplicateSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


class YamlDialect(Dialect):
    name = "yaml@1.2/json-compatible"
    aliases = ("yaml", "yml", "application/yaml", "application/x-yaml", "application/wellmanifest+yaml")
    media_types = ("application/yaml", "application/x-yaml", "application/wellmanifest+yaml")
    extensions = (".yaml", ".yml", ".wm.yaml", ".wm.yml")

    def parse(self, source: str, *, source_name: str | None = None) -> Document:
        cleaned, directives = split_runtime_prelude(source)
        data = yaml.load(cleaned, Loader=_NoDuplicateSafeLoader)
        self._assert_json_compatible(data)
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
        value: Any
        if projection == "data":
            value = document.data
        else:
            value = JsonDialect._ir_projection(document)
        self._assert_json_compatible(value)
        return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, default_flow_style=False)

    def probe(self, source: str, *, source_name: str | None = None) -> float:
        if source_name and source_name.lower().endswith((".yaml", ".yml")):
            return 0.8
        if ":" in source and "{" not in source[:20]:
            try:
                yaml.load(source, Loader=_NoDuplicateSafeLoader)
                return 0.45
            except yaml.YAMLError:
                return 0.0
        return 0.0

    @classmethod
    def _assert_json_compatible(cls, value: Any, path: str = "$" ) -> None:
        if value is None or isinstance(value, (str, bool, int, float)):
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                cls._assert_json_compatible(item, f"{path}[{index}]")
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError(f"YAML key at {path} must be a string for JSON-compatible profile")
                cls._assert_json_compatible(item, f"{path}.{key}")
            return
        raise ValueError(f"YAML value at {path} is not JSON-compatible: {type(value).__name__}")

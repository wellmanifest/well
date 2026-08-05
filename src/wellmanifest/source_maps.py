from __future__ import annotations

from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from .models import SourcePosition, SourceRange


def node_source_map(source: str) -> dict[str, SourceRange]:
    """Build a JSON-Pointer source map for JSON/YAML-compatible documents.

    PyYAML exposes stable start/end marks for both YAML and JSON input.  The
    function is used only for positions; JSON is still parsed by the strict JSON
    loader and YAML by the duplicate-key-safe loader.
    """

    try:
        node = yaml.compose(source)
    except yaml.YAMLError:
        return {}
    if node is None:
        return {}
    mappings: dict[str, SourceRange] = {}
    _walk_node(node, [], mappings)
    return mappings


def _walk_node(node: Node, path: list[str], mappings: dict[str, SourceRange]) -> None:
    pointer = _pointer(path)
    mappings[pointer] = _range(node)
    if isinstance(node, MappingNode):
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode):
                continue
            key = str(key_node.value)
            child_path = [*path, key]
            # Point object-property diagnostics at the key while retaining the
            # full value end position.
            mappings[_pointer(child_path)] = SourceRange(
                start=SourcePosition(line=key_node.start_mark.line + 1, column=key_node.start_mark.column + 1),
                end=SourcePosition(line=value_node.end_mark.line + 1, column=value_node.end_mark.column + 1),
            )
            _walk_node(value_node, child_path, mappings)
    elif isinstance(node, SequenceNode):
        for index, child in enumerate(node.value):
            _walk_node(child, [*path, str(index)], mappings)


def closest_range(source_map: dict[str, SourceRange], pointer: str) -> SourceRange | None:
    candidate = pointer
    while True:
        if candidate in source_map:
            return source_map[candidate]
        if not candidate:
            return source_map.get("")
        candidate = candidate.rsplit("/", 1)[0]


def serialize_source_map(
    source_map: dict[str, SourceRange],
    *,
    source: str,
    generated: str,
) -> dict[str, Any]:
    return {
        "schema": "wellm.source-map/v1",
        "source": source,
        "generated": generated,
        "mappings": {
            pointer: {
                "sourceLine": item.start.line,
                "sourceColumn": item.start.column,
                "endLine": item.end.line,
                "endColumn": item.end.column,
            }
            for pointer, item in sorted(source_map.items())
        },
    }


def _range(node: Node) -> SourceRange:
    return SourceRange(
        start=SourcePosition(line=node.start_mark.line + 1, column=node.start_mark.column + 1),
        end=SourcePosition(line=node.end_mark.line + 1, column=node.end_mark.column + 1),
    )


def _pointer(parts: list[str]) -> str:
    if not parts:
        return ""
    escaped = [part.replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(escaped)

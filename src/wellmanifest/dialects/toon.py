from __future__ import annotations

import re
from typing import Any

import yaml

from wellmanifest.models import Diagnostic, Document, DocumentMetadata, Severity, SourcePosition, SourceRange
from wellmanifest.source_maps import node_source_map

from .base import Dialect, DialectError
from .json_dialect import JsonDialect
from .yaml_dialect import YamlDialect, _NoDuplicateSafeLoader


class ToonDialect(Dialect):
    """TOON and code2llm ``map.toon.yaml`` adapter.

    Two compatible profiles are accepted:

    * JSON-model TOON/YAML data used for concise LLM interchange;
    * the compact structural-map profile emitted by code2llm, whose module rows
      and symbol rows intentionally omit YAML list markers.

    The latter is normalized to a JSON-compatible object and is therefore a
    semantic import, not a byte-for-byte formatter round-trip.
    """

    name = "toon@1"
    aliases = (
        "toon",
        "code2llm-toon",
        "code2llm-toon@1",
        "text/toon",
        "application/toon+yaml",
        "application/vnd.code2llm.toon+yaml",
        "application/wellmanifest+toon",
    )
    media_types = (
        "text/toon",
        "application/toon+yaml",
        "application/vnd.code2llm.toon+yaml",
        "application/wellmanifest+toon",
    )
    extensions = (".toon.yaml", ".toon.yml", ".toon")
    document_kind = "ir"

    _producer_re = re.compile(
        r"^#\s*producer:\s*(?P<producer>[^|]+?)\s*\|\s*artifact:\s*(?P<artifact>[^|]+?)"
        r"\s*\|\s*schema:\s*(?P<schema>\d+)\s*$",
        re.MULTILINE,
    )
    _modules_re = re.compile(r"^M\[(?P<count>\d+)\]:\s*$", re.MULTILINE)
    _short_list_keys = {"i": "imports", "e": "exports", "c": "classes", "f": "functions", "m": "methods"}

    def parse(self, source: str, *, source_name: str | None = None) -> Document:
        directives = self._directives(source)
        diagnostics: list[Diagnostic] = []
        source_map: dict[str, SourceRange] = {}
        try:
            data = yaml.load(source, Loader=_NoDuplicateSafeLoader)
            YamlDialect._assert_json_compatible(data)
            ir_kind = "toon-data"
            source_map = node_source_map(source)
        except yaml.YAMLError as exc:
            if not self._modules_re.search(source):
                mark = getattr(exc, "problem_mark", None)
                raise DialectError(
                    "WM-TOON-001",
                    f"Invalid TOON/YAML document: {exc}",
                    line=getattr(mark, "line", 0) + 1 if mark else None,
                    column=getattr(mark, "column", 0) + 1 if mark else None,
                ) from exc
            data, source_map, map_diagnostics = self._parse_code2llm_map(source)
            diagnostics.extend(map_diagnostics)
            directives["profile"] = "code2llm-map@1"
            ir_kind = "code2llm-structural-map"

        metadata = DocumentMetadata(
            source_dialect=self.name,
            document_kind="ir",
            schema_dialect="toon-schema@1",
            source_name=source_name,
            directives=directives,
        )
        return Document(
            metadata=metadata,
            data=data,
            ir={"kind": ir_kind, "schema": directives["toonSchema"], "value": data},
            diagnostics=diagnostics,
            source_text=source,
            source_map=source_map,
        )

    def _directives(self, source: str) -> dict[str, Any]:
        directives: dict[str, Any] = {"toonSchema": 1}
        match = self._producer_re.search(source)
        if match:
            directives.update(
                {
                    "producer": match.group("producer").strip(),
                    "artifact": match.group("artifact").strip(),
                    "toonSchema": int(match.group("schema")),
                }
            )
        return directives

    @classmethod
    def _parse_code2llm_map(
        cls, source: str
    ) -> tuple[dict[str, Any], dict[str, SourceRange], list[Diagnostic]]:
        modules: list[dict[str, Any]] = []
        details: dict[str, dict[str, Any]] = {}
        source_map: dict[str, SourceRange] = {}
        diagnostics: list[Diagnostic] = []
        section: str | None = None
        declared_modules: int | None = None
        current_file: str | None = None
        current_group: str | None = None

        def pointer(*parts: str) -> str:
            return "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in parts)

        def record(path: str, line: int, column: int, text: str) -> None:
            source_map[path] = SourceRange(
                start=SourcePosition(line=line, column=column),
                end=SourcePosition(line=line, column=column + max(1, len(text))),
            )

        for number, raw in enumerate(source.splitlines(), 1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            module_header = cls._modules_re.fullmatch(stripped)
            if module_header:
                section = "modules"
                declared_modules = int(module_header.group("count"))
                current_file = None
                current_group = None
                record("/modules", number, 1, stripped)
                continue
            if stripped == "D:":
                section = "details"
                current_file = None
                current_group = None
                record("/details", number, 1, stripped)
                continue

            if section == "modules":
                if indent < 2:
                    diagnostics.append(
                        Diagnostic(
                            code="WM-TOON-102",
                            severity=Severity.WARNING,
                            phase="parse",
                            dialect="toon@1",
                            message=f"Ignored unexpected top-level TOON line {number}: {stripped}",
                        )
                    )
                    continue
                path, separator, count_text = stripped.rpartition(",")
                if not separator or not count_text.isdigit():
                    diagnostics.append(
                        Diagnostic(
                            code="WM-TOON-103",
                            severity=Severity.WARNING,
                            phase="parse",
                            dialect="toon@1",
                            message=f"Malformed module row on line {number}: {stripped}",
                        )
                    )
                    modules.append({"path": stripped, "lines": None})
                else:
                    modules.append({"path": path, "lines": int(count_text)})
                record(pointer("modules", str(len(modules) - 1)), number, indent + 1, stripped)
                continue

            if section != "details":
                continue

            # A two-space key is a module/file. A few generated docstring labels
            # lose indentation; when already inside a file they are treated as a
            # symbol group rather than a new document section.
            if indent == 2 and stripped.endswith(":"):
                current_file = stripped[:-1]
                current_group = None
                details.setdefault(current_file, {"relations": {}, "symbols": {}, "members": []})
                record(pointer("details", current_file), number, indent + 1, stripped)
                continue
            if current_file is None:
                diagnostics.append(
                    Diagnostic(
                        code="WM-TOON-104",
                        severity=Severity.WARNING,
                        phase="parse",
                        dialect="toon@1",
                        message=f"Unattached detail row on line {number}: {stripped}",
                    )
                )
                continue

            detail = details[current_file]
            if stripped.endswith(":") and ": " not in stripped:
                current_group = stripped[:-1]
                detail["symbols"].setdefault(current_group, [])
                record(pointer("details", current_file, "symbols", current_group), number, indent + 1, stripped)
                continue

            if ": " in stripped:
                key, value = stripped.split(": ", 1)
                if key in cls._short_list_keys:
                    destination = cls._short_list_keys[key]
                    detail["relations"][destination] = [item for item in value.split(",") if item]
                    current_group = None
                    record(pointer("details", current_file, "relations", destination), number, indent + 1, stripped)
                else:
                    # Compact class/type signature, e.g. ``Client: run(1),close(0)``.
                    detail["symbols"][key] = [item.strip() for item in value.split(",") if item.strip()]
                    current_group = key
                    record(pointer("details", current_file, "symbols", key), number, indent + 1, stripped)
                continue

            if current_group is not None:
                detail["symbols"].setdefault(current_group, []).append(stripped)
                index = len(detail["symbols"][current_group]) - 1
                record(pointer("details", current_file, "symbols", current_group, str(index)), number, indent + 1, stripped)
            else:
                detail["members"].append(stripped)
                index = len(detail["members"]) - 1
                record(pointer("details", current_file, "members", str(index)), number, indent + 1, stripped)

        if declared_modules is not None and declared_modules != len(modules):
            diagnostics.append(
                Diagnostic(
                    code="WM-TOON-101",
                    severity=Severity.WARNING,
                    phase="parse",
                    dialect="toon@1",
                    message=f"TOON header declares {declared_modules} modules, parsed {len(modules)}.",
                )
            )
        return {
            "schema": "code2llm.structural-map/v1",
            "moduleCount": declared_modules if declared_modules is not None else len(modules),
            "modules": modules,
            "details": details,
        }, source_map, diagnostics

    def emit(self, document: Document, *, projection: str = "data", pretty: bool = True) -> str:
        value = document.data if projection == "data" else JsonDialect._ir_projection(document)
        YamlDialect._assert_json_compatible(value)
        producer = document.metadata.directives.get("producer", "wellm")
        artifact = document.metadata.directives.get("artifact", "manifest.toon.yaml")
        schema = document.metadata.directives.get("toonSchema", 1)
        body = yaml.safe_dump(value, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return f"# producer: {producer} | artifact: {artifact} | schema: {schema}\n{body}"

    def probe(self, source: str, *, source_name: str | None = None) -> float:
        if source_name and source_name.lower().endswith((".toon.yaml", ".toon.yml", ".toon")):
            return 0.995
        if self._producer_re.search(source) or self._modules_re.search(source):
            return 0.98
        return 0.0

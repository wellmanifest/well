from __future__ import annotations

import json
import re
from typing import Any, Iterator

from wellmanifest.models import Document, DocumentMetadata

from .base import Dialect, DialectError
from .common import split_runtime_prelude
from .json_dialect import JsonDialect


class Proto3Dialect(Dialect):
    name = "proto3"
    aliases = ("proto", "protobuf", "application/protobuf", "text/x-protobuf")
    media_types = ("application/protobuf", "text/x-protobuf")
    extensions = (".proto",)
    document_kind = "api"

    _block_start = re.compile(r"\b(message|enum|service)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")

    def parse(self, source: str, *, source_name: str | None = None) -> Document:
        cleaned, directives = split_runtime_prelude(source)
        syntax_match = re.search(r"\bsyntax\s*=\s*\"([^\"]+)\"\s*;", cleaned)
        if not syntax_match or syntax_match.group(1) != "proto3":
            raise DialectError("WM-PROTO-001", "Only `syntax = \"proto3\";` is supported")
        package_match = re.search(r"\bpackage\s+([A-Za-z_][A-Za-z0-9_.]*)\s*;", cleaned)
        options = [
            {"name": match.group(1), "value": match.group(2).strip()}
            for match in re.finditer(r"\boption\s+([A-Za-z_][A-Za-z0-9_.()]*)\s*=\s*([^;]+);", cleaned)
        ]
        messages: list[dict[str, Any]] = []
        enums: list[dict[str, Any]] = []
        services: list[dict[str, Any]] = []
        for kind, name, body in self._iter_blocks(cleaned):
            if kind == "message":
                messages.append(self._parse_message(name, body))
            elif kind == "enum":
                enums.append(self._parse_enum(name, body))
            else:
                services.append(self._parse_service(name, body))
        ir = {
            "kind": "api",
            "syntax": "proto3",
            "package": package_match.group(1) if package_match else None,
            "options": options,
            "messages": messages,
            "enums": enums,
            "services": services,
        }
        metadata = DocumentMetadata(
            source_dialect=self.name,
            document_kind="api",
            source_name=source_name,
            directives=directives,
        )
        return Document(metadata=metadata, data=None, ir=ir, source_text=source)

    def emit(self, document: Document, *, projection: str = "data", pretty: bool = True) -> str:
        if projection == "ir":
            return json.dumps(JsonDialect._ir_projection(document), ensure_ascii=False, indent=2) + "\n"
        ir = document.ir
        lines = ['syntax = "proto3";', ""]
        if ir.get("package"):
            lines.extend([f"package {ir['package']};", ""])
        for option in ir.get("options", []):
            lines.append(f"option {option['name']} = {option['value']};")
        if ir.get("options"):
            lines.append("")
        for enum in ir.get("enums", []):
            lines.append(f"enum {enum['name']} {{")
            for item in enum.get("values", []):
                lines.append(f"  {item['name']} = {item['number']};")
            lines.extend(["}", ""])
        for message in ir.get("messages", []):
            lines.append(f"message {message['name']} {{")
            for field in message.get("fields", []):
                label = f"{field['label']} " if field.get("label") else ""
                lines.append(f"  {label}{field['type']} {field['name']} = {field['number']};")
            lines.extend(["}", ""])
        for service in ir.get("services", []):
            lines.append(f"service {service['name']} {{")
            for rpc in service.get("rpcs", []):
                request = f"stream {rpc['request']}" if rpc.get("request_stream") else rpc["request"]
                response = f"stream {rpc['response']}" if rpc.get("response_stream") else rpc["response"]
                lines.append(f"  rpc {rpc['name']}({request}) returns ({response}) {{}}")
            lines.extend(["}", ""])
        return "\n".join(lines).rstrip() + "\n"

    def probe(self, source: str, *, source_name: str | None = None) -> float:
        if re.search(r"\bsyntax\s*=\s*\"proto3\"\s*;", source):
            return 1.0
        return 0.0

    def _iter_blocks(self, source: str) -> Iterator[tuple[str, str, str]]:
        position = 0
        while True:
            match = self._block_start.search(source, position)
            if not match:
                return
            open_index = match.end() - 1
            depth = 1
            index = open_index + 1
            in_string = False
            escaped = False
            while index < len(source) and depth:
                char = source[index]
                if escaped:
                    escaped = False
                elif char == "\\" and in_string:
                    escaped = True
                elif char == '"':
                    in_string = not in_string
                elif not in_string:
                    if char == "{":
                        depth += 1
                    elif char == "}":
                        depth -= 1
                index += 1
            if depth:
                raise DialectError("WM-PROTO-002", f"Unterminated {match.group(1)} {match.group(2)}")
            yield match.group(1), match.group(2), source[open_index + 1 : index - 1]
            position = index

    @staticmethod
    def _parse_message(name: str, body: str) -> dict[str, Any]:
        field_re = re.compile(
            r"(?m)^\s*(?:(repeated|optional)\s+)?([A-Za-z_][A-Za-z0-9_.<>]*)\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9]+)(?:\s*\[[^\]]*\])?\s*;"
        )
        fields = [
            {
                "label": match.group(1),
                "type": match.group(2),
                "name": match.group(3),
                "number": int(match.group(4)),
            }
            for match in field_re.finditer(body)
        ]
        return {"name": name, "fields": fields, "raw": body.strip()}

    @staticmethod
    def _parse_enum(name: str, body: str) -> dict[str, Any]:
        values = [
            {"name": match.group(1), "number": int(match.group(2))}
            for match in re.finditer(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(-?[0-9]+)\s*;", body)
        ]
        return {"name": name, "values": values, "raw": body.strip()}

    @staticmethod
    def _parse_service(name: str, body: str) -> dict[str, Any]:
        rpc_re = re.compile(
            r"rpc\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*(stream\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*\)\s*"
            r"returns\s*\(\s*(stream\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*\)",
            re.MULTILINE,
        )
        rpcs = [
            {
                "name": match.group(1),
                "request_stream": bool(match.group(2)),
                "request": match.group(3),
                "response_stream": bool(match.group(4)),
                "response": match.group(5),
            }
            for match in rpc_re.finditer(body)
        ]
        return {"name": name, "rpcs": rpcs, "raw": body.strip()}

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any

from wellmanifest.models import Diagnostic, Document, DocumentMetadata, Severity, SourcePosition, SourceRange

from .base import Dialect, DialectError
from .common import merge_duplicate, split_runtime_prelude
from .json_dialect import JsonDialect


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int


class Lexer:
    _identifier_start = re.compile(r"[A-Za-z_$]")
    _identifier_body = re.compile(r"[A-Za-z0-9_$./@+\-*?]")

    def __init__(self, source: str):
        self.source = source
        self.index = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self.index < len(self.source):
            ch = self.source[self.index]
            if ch in " \t\r":
                self._advance(ch)
                continue
            if ch == "\n":
                tokens.append(Token("NEWLINE", "\n", self.line, self.column))
                self._advance(ch)
                continue
            if ch == "#":
                tokens.append(self._comment())
                continue
            if ch in {'"', "'"}:
                tokens.append(self._string())
                continue
            if ch.isdigit() or (ch == "-" and self._peek(1).isdigit()):
                tokens.append(self._number())
                continue
            if self._identifier_start.match(ch):
                tokens.append(self._identifier())
                continue
            two = ch + self._peek(1)
            if two in {"->", "==", "!=", "<=", ">=", "&&", "||"}:
                token = Token("SYMBOL", two, self.line, self.column)
                self._advance(ch)
                self._advance(two[1])
                tokens.append(token)
                continue
            if ch in "{}[](),:=<>|&?":
                tokens.append(Token("SYMBOL", ch, self.line, self.column))
                self._advance(ch)
                continue
            raise DialectError("WM-PARSE-001", f"Unexpected character {ch!r}", line=self.line, column=self.column)
        tokens.append(Token("EOF", "", self.line, self.column))
        return tokens

    def _peek(self, offset: int) -> str:
        index = self.index + offset
        return self.source[index] if index < len(self.source) else ""

    def _advance(self, ch: str) -> None:
        self.index += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

    def _comment(self) -> Token:
        line, column = self.line, self.column
        start = self.index
        while self.index < len(self.source) and self.source[self.index] != "\n":
            self._advance(self.source[self.index])
        return Token("COMMENT", self.source[start + 1 : self.index].strip(), line, column)

    def _string(self) -> Token:
        quote = self.source[self.index]
        line, column = self.line, self.column
        start = self.index
        self._advance(quote)
        escaped = False
        while self.index < len(self.source):
            ch = self.source[self.index]
            self._advance(ch)
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == quote:
                return Token("STRING", self.source[start:self.index], line, column)
            if ch == "\n":
                raise DialectError("WM-PARSE-002", "Unterminated string", line=line, column=column)
        raise DialectError("WM-PARSE-002", "Unterminated string", line=line, column=column)

    def _number(self) -> Token:
        line, column = self.line, self.column
        start = self.index
        if self.source[self.index] == "-":
            self._advance("-")
        while self.index < len(self.source) and self.source[self.index].isdigit():
            self._advance(self.source[self.index])
        if self.index < len(self.source) and self.source[self.index] == ".":
            self._advance(".")
            while self.index < len(self.source) and self.source[self.index].isdigit():
                self._advance(self.source[self.index])
        if self.index < len(self.source) and self.source[self.index] in "eE":
            self._advance(self.source[self.index])
            if self.index < len(self.source) and self.source[self.index] in "+-":
                self._advance(self.source[self.index])
            while self.index < len(self.source) and self.source[self.index].isdigit():
                self._advance(self.source[self.index])
        return Token("NUMBER", self.source[start:self.index], line, column)

    def _identifier(self) -> Token:
        line, column = self.line, self.column
        start = self.index
        while self.index < len(self.source) and self._identifier_body.match(self.source[self.index]):
            self._advance(self.source[self.index])
        return Token("IDENT", self.source[start:self.index], line, column)


class StructuredParser:
    DECLARATION_KEYWORDS = {"type", "enum", "symbol", "variable", "predicate", "action", "service"}

    def __init__(self, source: str, *, dialect: str, source_name: str | None, strict_hcl: bool = False):
        self.original_source = source
        cleaned, self.directives = split_runtime_prelude(source)
        self.tokens = Lexer(cleaned).tokenize()
        self.position = 0
        self.dialect = dialect
        self.source_name = source_name
        self.strict_hcl = strict_hcl
        self.type_hints: dict[str, str] = {}
        self.pending_types: dict[str, str] = {}
        self.declarations: list[dict[str, Any]] = []
        self.diagnostics: list[Diagnostic] = []
        self.source_map: dict[str, SourceRange] = {}

    def parse(self) -> Document:
        data: dict[str, Any] = {}
        self._skip_layout()
        while not self._at("EOF"):
            if self._at_ident("data"):
                self._parse_data_declaration(data)
            elif self._at("IDENT") and self.current.value in self.DECLARATION_KEYWORDS:
                self._parse_named_declaration()
            else:
                parsed = self._parse_entry(path=[])
                if parsed is not None:
                    key, value = parsed
                    merge_duplicate(data, key, value)
            self._consume_statement_end()
            self._skip_layout()

        kind = self.directives.get("kind") or ("module" if self.declarations else "data")
        metadata = DocumentMetadata(
            source_dialect=self.dialect,
            document_kind=kind,
            schema_ref=self.directives.get("schema"),
            schema_dialect="json-schema@2020-12" if self.directives.get("schema") else None,
            source_name=self.source_name,
            directives=self.directives,
            type_hints=self.type_hints,
        )
        ir = {
            "kind": kind,
            "declarations": self.declarations,
            "data": data,
            "typeHints": self.type_hints,
        }
        return Document(
            metadata=metadata,
            data=data,
            ir=ir,
            diagnostics=self.diagnostics,
            source_text=self.original_source,
            source_map=self.source_map,
        )

    @property
    def current(self) -> Token:
        return self.tokens[self.position]

    def _peek(self, offset: int = 1) -> Token:
        return self.tokens[min(self.position + offset, len(self.tokens) - 1)]

    def _at(self, kind: str, value: str | None = None) -> bool:
        return self.current.kind == kind and (value is None or self.current.value == value)

    def _at_ident(self, value: str) -> bool:
        return self._at("IDENT") and self.current.value.lower() == value.lower()

    def _advance(self) -> Token:
        token = self.current
        if token.kind != "EOF":
            self.position += 1
        return token

    def _expect(self, kind: str, value: str | None = None) -> Token:
        if not self._at(kind, value):
            expected = value if value is not None else kind
            raise DialectError(
                "WM-PARSE-003",
                f"Expected {expected!r}, found {self.current.value!r}",
                line=self.current.line,
                column=self.current.column,
            )
        return self._advance()

    def _skip_layout(self) -> None:
        while self._at("NEWLINE") or self._at("COMMENT") or self._at("SYMBOL", ","):
            self._advance()

    def _consume_statement_end(self) -> None:
        while self._at("COMMENT") or self._at("SYMBOL", ","):
            self._advance()
        if self._at("NEWLINE"):
            self._advance()

    def _parse_named_declaration(self) -> None:
        keyword = self._advance()
        name = self._expect_any_name()
        header_tokens: list[str] = []
        while not self._at("EOF") and not self._at("NEWLINE") and not self._at("SYMBOL", "{") and not self._at("SYMBOL", "="):
            header_tokens.append(self._advance().value)
        declaration: dict[str, Any] = {
            "kind": keyword.value.lower(),
            "name": name,
            "header": " ".join(header_tokens).strip(),
            "line": keyword.line,
        }
        if self._at("SYMBOL", "="):
            self._advance()
            declaration["value"] = self._parse_value(path=["$declarations", name])
        elif self._at("SYMBOL", "{"):
            declaration["body"] = self._capture_balanced_block()
        self.declarations.append(declaration)

    def _capture_balanced_block(self) -> str:
        self._expect("SYMBOL", "{")
        depth = 1
        parts = ["{"]
        while depth > 0 and not self._at("EOF"):
            token = self._advance()
            parts.append(token.value)
            if token.kind == "SYMBOL" and token.value == "{":
                depth += 1
            elif token.kind == "SYMBOL" and token.value == "}":
                depth -= 1
        if depth != 0:
            raise DialectError("WM-PARSE-004", "Unterminated declaration block")
        return " ".join(parts)

    def _parse_data_declaration(self, target: dict[str, Any]) -> None:
        self._advance()  # data
        name = self._expect_any_name()
        type_name: str | None = None
        if self._at("SYMBOL", ":"):
            self._advance()
            type_name = self._parse_type_expression(stop_on_newline=False)
        self._expect("SYMBOL", "=")
        path = [name]
        value = self._parse_value(path=path)
        merge_duplicate(target, name, value)
        if type_name:
            self.type_hints[self._path(path)] = type_name

    def _parse_entry(self, *, path: list[str]) -> tuple[str, Any] | None:
        key_token = self.current
        key = self._expect_any_name()

        labels: list[str] = []
        while self._at("STRING") or (
            self._at("IDENT") and self._peek().kind == "STRING"
        ):
            labels.append(str(self._parse_scalar_token(self._advance())))

        current_path = [*path, key]
        path_key = self._path(current_path)
        self.source_map[path_key] = SourceRange(
            start=SourcePosition(line=key_token.line, column=key_token.column),
            end=SourcePosition(line=key_token.line, column=key_token.column + max(1, len(key_token.value))),
        )

        if self._at("SYMBOL", "{"):
            value = self._parse_object(path=current_path)
            if labels:
                value = {"$labels": labels, **value}
            return key, value

        if labels and self._at("SYMBOL", "{"):
            value = self._parse_object(path=current_path)
            value = {"$labels": labels, **value}
            return key, value

        explicit_type: str | None = None
        if self._at("SYMBOL", ":"):
            colon = self._advance()
            explicit_type = self._parse_type_expression(stop_on_newline=True)
            if self.strict_hcl:
                self.diagnostics.append(
                    Diagnostic(
                        code="WM-HCL-101",
                        severity=Severity.ERROR,
                        phase="parse",
                        dialect=self.dialect,
                        source=self.source_name,
                        message=f"Inline type annotation for {key!r} is not valid HCL syntax.",
                        hint="Use an external schema or the typed@1 dialect.",
                        range=SourceRange(
                            start=SourcePosition(line=colon.line, column=colon.column),
                            end=SourcePosition(line=colon.line, column=colon.column + 1),
                        ),
                    )
                )
            if not self._at("SYMBOL", "="):
                self.pending_types[path_key] = explicit_type
                self.type_hints[path_key] = explicit_type
                self.diagnostics.append(
                    Diagnostic(
                        code="WM-TYPE-101",
                        severity=Severity.INFO,
                        phase="parse",
                        dialect=self.dialect,
                        source=self.source_name,
                        path=path_key,
                        message=f"Split declaration registered for {key!r}; canonical form is `{key}: {explicit_type} = ...`.",
                    )
                )
                return None

        if self._at("SYMBOL", "="):
            self._advance()
            value = self._parse_value(path=current_path)
            type_name = explicit_type or self.pending_types.get(path_key)
            if type_name:
                self.type_hints[path_key] = type_name
            if self._at("COMMENT"):
                comment = self.current.value.strip()
                if comment:
                    hint = comment[6:].strip() if comment.startswith("@type ") else comment.split()[0]
                    if hint and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_.$<>\[\]|? -]*", hint):
                        if path_key not in self.type_hints:
                            self.type_hints[path_key] = hint
                        self.diagnostics.append(
                            Diagnostic(
                                code="WM-TYPE-102",
                                severity=Severity.WARNING,
                                phase="parse",
                                dialect=self.dialect,
                                source=self.source_name,
                                path=path_key,
                                message=f"Comment type hint {hint!r} is non-normative unless confirmed by a schema.",
                                hint="Use `field: Type = value` in typed@1 or attach JSON Schema in hcl@2.",
                            )
                        )
            return key, value

        raise DialectError(
            "WM-PARSE-005",
            f"Expected '{{', ':', or '=' after {key!r}",
            line=key_token.line,
            column=key_token.column,
        )

    def _parse_type_expression(self, *, stop_on_newline: bool) -> str:
        parts: list[str] = []
        square = paren = angle = 0
        while not self._at("EOF"):
            if self._at("SYMBOL", "=") and square == paren == angle == 0:
                break
            if stop_on_newline and self._at("NEWLINE") and square == paren == angle == 0:
                break
            if self._at("SYMBOL", "}") and square == paren == angle == 0:
                break
            token = self.current
            if token.kind == "COMMENT" and square == paren == angle == 0:
                break
            self._advance()
            if token.kind == "SYMBOL":
                if token.value == "[":
                    square += 1
                elif token.value == "]":
                    square -= 1
                elif token.value == "(":
                    paren += 1
                elif token.value == ")":
                    paren -= 1
                elif token.value == "<":
                    angle += 1
                elif token.value == ">":
                    angle -= 1
            parts.append(token.value)
        rendered = self._join_type_tokens(parts).strip()
        if not rendered:
            raise DialectError(
                "WM-PARSE-006",
                "Expected a type expression",
                line=self.current.line,
                column=self.current.column,
            )
        return rendered

    @staticmethod
    def _join_type_tokens(parts: list[str]) -> str:
        text = " ".join(parts)
        replacements = {
            "[ ": "[",
            " ]": "]",
            "< ": "<",
            " >": ">",
            "( ": "(",
            " )": ")",
            " ,": ",",
            " | ": " | ",
            " ?": "?",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _parse_object(self, *, path: list[str]) -> dict[str, Any]:
        self._expect("SYMBOL", "{")
        result: dict[str, Any] = {}
        self._skip_layout()
        while not self._at("SYMBOL", "}"):
            if self._at("EOF"):
                raise DialectError("WM-PARSE-007", "Unterminated object block")
            parsed = self._parse_entry(path=path)
            if parsed is not None:
                key, value = parsed
                merge_duplicate(result, key, value)
            self._consume_statement_end()
            self._skip_layout()
        self._advance()
        return result

    def _parse_value(self, *, path: list[str]) -> Any:
        token = self.current
        pointer = self._path(path)
        self.source_map[pointer] = SourceRange(
            start=SourcePosition(line=token.line, column=token.column),
            end=SourcePosition(line=token.line, column=token.column + max(1, len(token.value))),
        )
        if self._at("SYMBOL", "{"):
            return self._parse_object(path=path)
        if self._at("SYMBOL", "["):
            return self._parse_list(path=path)
        if token.kind in {"STRING", "NUMBER"}:
            self._advance()
            return self._parse_scalar_token(token)
        if token.kind == "IDENT":
            self._advance()
            lower = token.value.lower()
            if lower == "true":
                return True
            if lower == "false":
                return False
            if lower in {"null", "none"}:
                return None
            if self._at("SYMBOL", "("):
                self._advance()
                args: list[Any] = []
                self._skip_layout()
                while not self._at("SYMBOL", ")"):
                    args.append(self._parse_value(path=[*path, f"$arg{len(args)}"]))
                    if self._at("SYMBOL", ","):
                        self._advance()
                    self._skip_layout()
                self._advance()
                return {"$call": token.value, "args": args}
            return token.value
        raise DialectError(
            "WM-PARSE-008",
            f"Expected value, found {token.value!r}",
            line=token.line,
            column=token.column,
        )

    def _parse_list(self, *, path: list[str]) -> list[Any]:
        self._expect("SYMBOL", "[")
        result: list[Any] = []
        self._skip_layout()
        while not self._at("SYMBOL", "]"):
            if self._at("EOF"):
                raise DialectError("WM-PARSE-009", "Unterminated list")
            result.append(self._parse_value(path=[*path, str(len(result))]))
            if self._at("SYMBOL", ","):
                self._advance()
            self._skip_layout()
        self._advance()
        return result

    @staticmethod
    def _parse_scalar_token(token: Token) -> Any:
        if token.kind == "NUMBER":
            return float(token.value) if any(char in token.value for char in ".eE") else int(token.value)
        if token.kind == "STRING":
            try:
                return json.loads(token.value) if token.value.startswith('"') else ast.literal_eval(token.value)
            except (json.JSONDecodeError, ValueError, SyntaxError) as exc:
                raise DialectError("WM-PARSE-010", f"Invalid string literal: {exc}", line=token.line, column=token.column) from exc
        return token.value

    def _expect_any_name(self) -> str:
        if self.current.kind not in {"IDENT", "STRING"}:
            raise DialectError(
                "WM-PARSE-011",
                f"Expected identifier, found {self.current.value!r}",
                line=self.current.line,
                column=self.current.column,
            )
        token = self._advance()
        return str(self._parse_scalar_token(token))

    @staticmethod
    def _path(parts: list[str]) -> str:
        return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


class StructuredEmitter:
    def __init__(self, *, typed: bool):
        self.typed = typed

    def emit(self, document: Document, *, projection: str, pretty: bool) -> str:
        if projection == "ir":
            return json.dumps(JsonDialect._ir_projection(document), ensure_ascii=False, indent=2) + "\n"
        if not isinstance(document.data, dict):
            raise ValueError("HCL/typed document root must be an object")
        lines: list[str] = []
        for key, value in document.data.items():
            path = f"/{key}"
            type_name = document.metadata.type_hints.get(path)
            if self.typed and type_name:
                lines.extend(self._emit_typed_data(key, type_name, value, document, path))
            elif isinstance(value, dict):
                lines.append(f"{self._key(key)} {{")
                lines.extend(self._emit_object(value, document, path, indent=1))
                lines.append("}")
            elif isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                # Repeated HCL blocks cannot distinguish a singleton object from a
                # singleton list after parsing.  The canonical data projection
                # therefore emits an explicit list expression for both HCL and
                # typed WellManifest.  External idiomatic repeated blocks remain
                # accepted by the parser.
                lines.append(f"{self._key(key)} = {self._format_value(value, document, path, 0)}")
            else:
                prefix = f"{self._key(key)}"
                if self.typed and type_name:
                    prefix += f": {type_name}"
                lines.append(f"{prefix} = {self._format_value(value, document, path, 0)}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _emit_typed_data(self, key: str, type_name: str, value: Any, document: Document, path: str) -> list[str]:
        if isinstance(value, dict):
            lines = [f"data {self._key(key)}: {type_name} = {{"]
            lines.extend(self._emit_object(value, document, path, indent=1))
            lines.append("}")
            return lines
        return [f"data {self._key(key)}: {type_name} = {self._format_value(value, document, path, 0)}"]

    def _emit_object(
        self,
        mapping: dict[str, Any],
        document: Document,
        base_path: str,
        *,
        indent: int,
    ) -> list[str]:
        lines: list[str] = []
        pad = "  " * indent
        for key, value in mapping.items():
            if key == "$labels":
                continue
            path = f"{base_path}/{str(key).replace('~', '~0').replace('/', '~1')}"
            type_name = document.metadata.type_hints.get(path)
            prefix = f"{pad}{self._key(key)}"
            if self.typed and type_name:
                prefix += f": {type_name}"
            if isinstance(value, dict):
                # Nested mappings are emitted as object-valued attributes in
                # both dialects.  This is valid HCL inside ordinary blocks and,
                # unlike a nested block, is also valid inside list/object
                # expressions used for lossless JSON-compatible round-trips.
                lines.append(f"{prefix} = {{")
                lines.extend(self._emit_object(value, document, path, indent=indent + 1))
                lines.append(f"{pad}}}")
            else:
                lines.append(f"{prefix} = {self._format_value(value, document, path, indent)}")
        return lines

    def _format_value(self, value: Any, document: Document, path: str, indent: int) -> str:
        if value is None:
            return "null"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            type_name = document.metadata.type_hints.get(path, "")
            if self.typed and (type_name.endswith("State") or type_name.startswith("enum ")) and re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
                return value
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, list):
            if not value:
                return "[]"
            if all(not isinstance(item, (dict, list)) for item in value):
                return "[" + ", ".join(self._format_value(item, document, f"{path}/{index}", indent) for index, item in enumerate(value)) + "]"
            inner: list[str] = ["["]
            pad = "  " * (indent + 1)
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    inner.append(pad + "{")
                    inner.extend(self._emit_object(item, document, f"{path}/{index}", indent=indent + 2))
                    inner.append(pad + "},")
                else:
                    inner.append(pad + self._format_value(item, document, f"{path}/{index}", indent + 1) + ",")
            inner.append("  " * indent + "]")
            return "\n".join(inner)
        if isinstance(value, dict) and "$call" in value:
            return f"{value['$call']}(" + ", ".join(self._format_value(item, document, path, indent) for item in value.get("args", [])) + ")"
        if isinstance(value, dict):
            lines = ["{"]
            lines.extend(self._emit_object(value, document, path, indent=indent + 1))
            lines.append("  " * indent + "}")
            return "\n".join(lines)
        raise TypeError(f"Unsupported value {type(value).__name__}")

    @staticmethod
    def _key(key: str) -> str:
        return key if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$-]*", key) else json.dumps(key, ensure_ascii=False)


class HclDialect(Dialect):
    name = "hcl@2"
    aliases = ("hcl", "application/hcl", "application/wellmanifest+hcl")
    media_types = ("application/hcl", "application/wellmanifest+hcl")
    extensions = (".hcl", ".tf", ".wm.hcl")

    def parse(self, source: str, *, source_name: str | None = None) -> Document:
        return StructuredParser(source, dialect=self.name, source_name=source_name, strict_hcl=True).parse()

    def emit(self, document: Document, *, projection: str = "data", pretty: bool = True) -> str:
        return StructuredEmitter(typed=False).emit(document, projection=projection, pretty=pretty)

    def probe(self, source: str, *, source_name: str | None = None) -> float:
        if source_name and source_name.lower().endswith((".hcl", ".tf")):
            return 0.9
        if re.search(r"^[A-Za-z_$][\w$-]*\s*\{", source, re.MULTILINE) and "=" in source:
            return 0.62
        return 0.0


class TypedDialect(Dialect):
    name = "typed@1"
    aliases = ("typed", "wellmanifest", "wm", "application/wellmanifest+typed")
    media_types = ("application/wellmanifest+typed",)
    extensions = (".wm", ".wellmanifest", ".typed")

    def parse(self, source: str, *, source_name: str | None = None) -> Document:
        return StructuredParser(source, dialect=self.name, source_name=source_name, strict_hcl=False).parse()

    def emit(self, document: Document, *, projection: str = "data", pretty: bool = True) -> str:
        return StructuredEmitter(typed=True).emit(document, projection=projection, pretty=pretty)

    def probe(self, source: str, *, source_name: str | None = None) -> float:
        if source_name and source_name.lower().endswith((".wm", ".wellmanifest", ".typed")):
            return 0.95
        if re.search(r"\b(?:type|enum|data)\s+[A-Za-z_]", source) or re.search(r"\w+\s*:\s*[A-Za-z_][\w.<>\[\]|?]*\s*=", source):
            return 0.8
        return 0.25 if "#@wellmanifest" in source else 0.0

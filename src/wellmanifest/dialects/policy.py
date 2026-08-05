from __future__ import annotations

import json
import re
from typing import Any

from wellmanifest.models import Diagnostic, Document, DocumentMetadata, Severity, SourcePosition, SourceRange

from .base import Dialect
from .common import split_runtime_prelude
from .json_dialect import JsonDialect


class PolicyDialect(Dialect):
    name = "policy-sh@1"
    aliases = ("policy", "policy-sh", "dsl-policy", "wellm-policy", "application/wellmanifest+policy")
    media_types = ("application/wellmanifest+policy",)
    extensions = (".policy", ".policy.dsl", ".dsl")
    document_kind = "policy"

    canonical_fences = ("dsl", "policy", "wellm-policy")
    compatibility_fences = ("bash", "sh", "shell")

    _rule_re = re.compile(r"^RULE\s+(\S+)(?:\s+TYPE\s+(\S+))?\s*$", re.IGNORECASE)
    _transition_re = re.compile(r"^TRANSITION\s+(\S+)\s*->\s*(\S+)(?:\s+WHEN\s+(.+))?$", re.IGNORECASE)
    _fence_re = re.compile(r"^```([^\n`]*)\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)

    def parse(self, source: str, *, source_name: str | None = None) -> Document:
        cleaned, directives = split_runtime_prelude(source)
        cleaned, fence_diagnostics = self._extract_dsl(cleaned, source_name=source_name)
        metadata_values: dict[str, Any] = {}
        rules: list[dict[str, Any]] = []
        states: list[str] = []
        transitions: list[dict[str, Any]] = []
        statements: list[str] = []
        current_rule: dict[str, Any] | None = None

        lines = cleaned.splitlines()
        index = 0
        while index < len(lines):
            raw = lines[index]
            line = self._strip_comment(raw).strip()
            index += 1
            if not line:
                continue

            rule_match = self._rule_re.match(line)
            if rule_match:
                current_rule = {
                    "kind": "rule",
                    "id": rule_match.group(1),
                    "type": (rule_match.group(2) or "REQUIRED").upper(),
                    "when": None,
                    "actions": [],
                    "forbids": [],
                    "assertions": [],
                    "next": [],
                    "sourceLine": index,
                }
                rules.append(current_rule)
                continue

            if line.upper().startswith("STATE "):
                current_rule = None
                states.append(line.split(None, 1)[1].strip())
                continue

            transition_match = self._transition_re.match(line)
            if transition_match:
                current_rule = None
                transitions.append(
                    {
                        "from": transition_match.group(1),
                        "to": transition_match.group(2),
                        "when": transition_match.group(3),
                        "sourceLine": index,
                    }
                )
                continue

            if current_rule is not None:
                upper = line.upper()
                if upper.startswith("WHEN "):
                    current_rule["when"] = line[5:].strip()
                elif upper.startswith("DO "):
                    current_rule["actions"].append(self._parse_action(line[3:].strip()))
                elif upper.startswith("FORBID "):
                    current_rule["forbids"].append(self._parse_action(line[7:].strip()))
                elif upper.startswith("ASSERT "):
                    current_rule["assertions"].append(line[7:].strip())
                elif upper.startswith("NEXT "):
                    current_rule["next"].append(line[5:].strip())
                else:
                    current_rule.setdefault("raw", []).append(line)
                continue

            assignment = re.match(
                r"^(DOCUMENT|VERSION|LANGUAGE|MODE|PURPOSE|POLICY)\s+(.+)$",
                line,
                re.IGNORECASE,
            )
            if assignment:
                metadata_values.setdefault(assignment.group(1).lower(), self._literal_or_text(assignment.group(2)))
                continue

            statements.append(line)

        ir = {
            "kind": "policy",
            "metadata": metadata_values,
            "rules": rules,
            "states": states,
            "transitions": transitions,
            "statements": statements,
        }
        data = {
            "document": metadata_values,
            "rules": rules,
            "stateMachine": {"states": states, "transitions": transitions},
            "statements": statements,
        }
        metadata = DocumentMetadata(
            source_dialect=self.name,
            document_kind="policy",
            source_name=source_name,
            directives=directives,
        )
        return Document(
            metadata=metadata,
            data=data,
            ir=ir,
            diagnostics=fence_diagnostics,
            source_text=source,
        )

    def emit(self, document: Document, *, projection: str = "data", pretty: bool = True) -> str:
        if projection == "ir":
            return json.dumps(JsonDialect._ir_projection(document), ensure_ascii=False, indent=2) + "\n"
        ir = document.ir
        lines: list[str] = []
        for key in ("document", "version", "language", "mode", "purpose", "policy"):
            if key in ir.get("metadata", {}):
                lines.append(f"{key.upper()} {self._format_literal(ir['metadata'][key])}")
        if lines:
            lines.append("")
        for statement in ir.get("statements", []):
            lines.append(statement)
        if ir.get("statements"):
            lines.append("")
        for state in ir.get("states", []):
            lines.append(f"STATE {state}")
        for transition in ir.get("transitions", []):
            line = f"TRANSITION {transition['from']} -> {transition['to']}"
            if transition.get("when"):
                line += f" WHEN {transition['when']}"
            lines.append(line)
        if ir.get("states") or ir.get("transitions"):
            lines.append("")
        for rule in ir.get("rules", []):
            header = f"RULE {rule['id']}"
            if rule.get("type") and rule.get("type") != "REQUIRED":
                header += f" TYPE {rule['type']}"
            lines.append(header)
            if rule.get("when"):
                lines.append(f"WHEN {rule['when']}")
            for action in rule.get("actions", []):
                lines.append(f"DO {action['text']}")
            for action in rule.get("forbids", []):
                lines.append(f"FORBID {action['text']}")
            for assertion in rule.get("assertions", []):
                lines.append(f"ASSERT {assertion}")
            for next_state in rule.get("next", []):
                lines.append(f"NEXT {next_state}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def probe(self, source: str, *, source_name: str | None = None) -> float:
        if re.search(r"^RULE\s+[A-Za-z0-9_.:-]+", source, re.MULTILINE) and re.search(
            r"^(WHEN|DO|FORBID|ASSERT)\s+", source, re.MULTILINE
        ):
            return 0.98
        if re.search(r"```(?:dsl|policy|wellm-policy)\b", source, re.IGNORECASE) and "RULE " in source:
            return 0.9
        if re.search(r"```(?:bash|sh|shell)\b", source, re.IGNORECASE) and "RULE " in source:
            return 0.75
        return 0.0

    @classmethod
    def _extract_dsl(
        cls,
        source: str,
        *,
        source_name: str | None,
    ) -> tuple[str, list[Diagnostic]]:
        matches = list(cls._fence_re.finditer(source))
        if not matches:
            return source, []

        output = ["" for _ in source.splitlines()]
        diagnostics: list[Diagnostic] = []
        recognized = 0
        for match in matches:
            info = match.group(1).strip()
            language = (info.split()[0] if info else "").lower()
            body = match.group(2)
            canonical = language in cls.canonical_fences
            compatibility = language in cls.compatibility_fences and cls.looks_like_policy(body)
            if not canonical and not compatibility:
                continue
            recognized += 1
            body_start_line = source[: match.start(2)].count("\n")
            for offset, line in enumerate(body.splitlines()):
                target = body_start_line + offset
                if target < len(output):
                    output[target] = line
            if compatibility:
                opening_line = source[: match.start()].count("\n") + 1
                diagnostics.append(
                    Diagnostic(
                        code="WM-POLICY-101",
                        severity=Severity.WARNING,
                        phase="parse",
                        dialect=cls.name,
                        source=source_name,
                        message=(
                            f"Policy-shaped fenced block uses `{language}`. "
                            "Canonical fences are `dsl`, `policy`, or `wellm-policy`."
                        ),
                        hint="Run `wellm policy fmt <file> --rewrite-fences`.",
                        range=SourceRange(
                            start=SourcePosition(line=opening_line, column=1),
                            end=SourcePosition(line=opening_line, column=max(4, len(match.group(1)) + 4)),
                        ),
                    )
                )
        return ("\n".join(output) if recognized else source), diagnostics

    @staticmethod
    def looks_like_policy(body: str) -> bool:
        first = next((line.strip() for line in body.splitlines() if line.strip()), "")
        return bool(
            re.match(
                r"^(?:RULE|STATE|TRANSITION|DOCUMENT|VERSION|LANGUAGE|MODE|PURPOSE|POLICY|DONE|REPORT)\b",
                first,
                re.IGNORECASE,
            )
        )

    @classmethod
    def rewrite_fences(cls, source: str, *, target: str = "wellm-policy") -> tuple[str, int]:
        replacements = 0

        def replace(match: re.Match[str]) -> str:
            nonlocal replacements
            info = match.group(1).strip()
            language = (info.split()[0] if info else "").lower()
            body = match.group(2)
            if language in cls.compatibility_fences and cls.looks_like_policy(body):
                replacements += 1
                return f"```{target}\n{body}```"
            return match.group(0)

        return cls._fence_re.sub(replace, source), replacements

    @staticmethod
    def _strip_comment(line: str) -> str:
        in_quote: str | None = None
        escaped = False
        for index, char in enumerate(line):
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char in {'"', "'"}:
                if in_quote == char:
                    in_quote = None
                elif in_quote is None:
                    in_quote = char
                continue
            if char == "#" and in_quote is None:
                return line[:index]
        return line

    @staticmethod
    def _parse_action(text: str) -> dict[str, Any]:
        words = text.split()
        return {
            "verb": words[0] if words else "",
            "arguments": words[1:],
            "text": text,
        }

    @staticmethod
    def _literal_or_text(value: str) -> Any:
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        if stripped.startswith('"') and stripped.endswith('"'):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return stripped[1:-1]
        return stripped

    @staticmethod
    def _format_literal(value: Any) -> str:
        if isinstance(value, str) and (" " in value or not re.fullmatch(r"[A-Za-z0-9_.:/-]+", value)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

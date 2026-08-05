from __future__ import annotations

import json
import re
from typing import Any

_DIRECTIVE_RE = re.compile(r"^\s*#@(?:wellmanifest|dslrt)\s+(.*)$")
_PAIR_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*(\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*'|[^\s]+)")


def split_runtime_prelude(source: str) -> tuple[str, dict[str, Any]]:
    """Remove an OS shebang and WellManifest directives before dialect parsing."""
    lines = source.splitlines()
    directives: dict[str, Any] = {}
    kept: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if index == 0 and stripped.startswith("#!"):
            directives["shebang"] = stripped
            kept.append("")
            continue
        match = _DIRECTIVE_RE.match(line)
        if match:
            for key, raw in _PAIR_RE.findall(match.group(1)):
                value = raw
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    try:
                        value = json.loads(value) if value.startswith('"') else value[1:-1]
                    except json.JSONDecodeError:
                        value = value[1:-1]
                elif value.lower() in {"true", "false"}:
                    value = value.lower() == "true"
                directives[key] = value
            kept.append("")
            continue
        kept.append(line)
    return "\n".join(kept), directives


def json_pointer(parts: list[Any]) -> str:
    if not parts:
        return ""
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(escaped)


def merge_duplicate(target: dict[str, Any], key: str, value: Any) -> None:
    if key not in target:
        target[key] = value
        return
    current = target[key]
    if isinstance(current, list) and current and all(isinstance(item, dict) for item in current):
        current.append(value)
    else:
        target[key] = [current, value]

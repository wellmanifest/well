from __future__ import annotations

import json
import os
import re
import shutil
from ipaddress import ip_network
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft202012Validator


ENV_SCHEMA = "wellm.env-contract/v1"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def contract_paths(root: str | Path | None = None) -> tuple[Path, Path]:
    project_root = Path(root).resolve() if root else _project_root()
    return (
        project_root / "config" / "env-contract.json",
        project_root / "src" / "wellmanifest" / "resources" / "env-contract.json",
    )


def load_env_contract(path: str | Path | None = None) -> dict[str, Any]:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    repository, packaged = contract_paths()
    candidate = repository if repository.exists() else packaged
    return json.loads(candidate.read_text(encoding="utf-8"))


def render_env_example(contract: dict[str, Any]) -> str:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in contract.get("variables", []):
        groups.setdefault(str(item["group"]), []).append(item)
    lines = [
        "# Generated from config/env-contract.json by `make env-sync`.",
        "# Copy to .env and keep secrets local. Values below are development defaults.",
        "",
    ]
    for group in sorted(groups):
        lines.append(f"# [{group}]")
        for item in sorted(groups[group], key=lambda value: value["name"]):
            lines.append(f"# {item['description']}")
            if item.get("secret"):
                lines.append("# secret: never commit a real value")
            lines.append(f"{item['name']}={item.get('default', '')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def sync_env_contract(root: str | Path | None = None, *, check: bool = False) -> dict[str, Any]:
    project_root = Path(root).resolve() if root else _project_root()
    contract = json.loads((project_root / "config" / "env-contract.json").read_text(encoding="utf-8"))
    rendered = render_env_example(contract)
    targets = [project_root / ".env.example", project_root / "src" / "wellmanifest" / "resources" / "env-contract.json"]
    expected = [rendered, json.dumps(contract, ensure_ascii=False, indent=2) + "\n"]
    drift: list[str] = []
    for path, content in zip(targets, expected, strict=True):
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                drift.append(path.as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if drift:
        raise ValueError("Environment contract drift: " + ", ".join(drift))
    return contract


def setup_env(root: str | Path | None = None, *, force: bool = False) -> Path:
    project_root = Path(root).resolve() if root else _project_root()
    sync_env_contract(project_root)
    source = project_root / ".env.example"
    target = project_root / ".env"
    if target.exists() and not force:
        return target
    shutil.copyfile(source, target)
    try:
        target.chmod(0o600)
    except OSError:
        pass
    return target


def parse_dotenv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid .env line {number}: expected NAME=value")
        name, value = line.split("=", 1)
        name = name.strip()
        if name in values:
            raise ValueError(f"Duplicate .env variable {name!r} on line {number}")
        values[name] = value
    return values


def _validate_value(item: dict[str, Any], value: str) -> str | None:
    if not value and not item.get("required"):
        return None
    value_type = item.get("type")
    try:
        if value_type == "integer":
            int(value)
        elif value_type == "number":
            float(value)
        elif value_type == "boolean" and value.lower() not in {"0", "1", "true", "false", "yes", "no"}:
            return "expected boolean 0/1/true/false"
        elif value_type == "url":
            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                return "expected absolute URL"
        elif value_type == "cidr":
            ip_network(value, strict=False)
    except (ValueError, TypeError) as exc:
        return str(exc)
    return None


def referenced_environment_variables(root: str | Path | None = None) -> set[str]:
    project_root = Path(root).resolve() if root else _project_root()
    references: set[str] = set()
    text_patterns = [
        re.compile(r"os\.getenv\(\s*[\"']([A-Z][A-Z0-9_]+)"),
        re.compile(r"os\.environ\.get\(\s*[\"']([A-Z][A-Z0-9_]+)"),
        re.compile(r"process\.env\.([A-Z][A-Z0-9_]+)"),
        re.compile(r"\$\{([A-Z][A-Z0-9_]+)(?::?[-+?][^}]*)?\}"),
    ]
    candidates: list[Path] = []
    for relative in ("src", "scripts", "examples", "packages"):
        base = project_root / relative
        if base.exists():
            candidates.extend(path for path in base.rglob("*") if path.is_file())
    candidates.extend(project_root.glob("compose*.yml"))
    candidates.extend(project_root.glob("compose*.yaml"))
    candidates.extend([project_root / "Dockerfile", project_root / "Makefile"])
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in text_patterns:
            references.update(pattern.findall(text))
    controlled_prefixes = (
        "WELLMANIFEST_",
        "URIRUN_",
        "TODO2CODE_",
        "OPENROUTER_",
    )
    return {
        name
        for name in references
        if name == "MQTT_HOST" or name.startswith(controlled_prefixes)
    }


def verify_env_contract(root: str | Path | None = None, *, dotenv: str | Path | None = None) -> dict[str, Any]:
    project_root = Path(root).resolve() if root else _project_root()
    contract_path = project_root / "config" / "env-contract.json"
    schema_path = project_root / "schemas" / "env-contract.schema.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(contract)
    names = [str(item["name"]) for item in contract["variables"]]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    declared = set(names)
    ignored = set(contract.get("ignoredReferences", []))
    referenced = referenced_environment_variables(project_root) - ignored
    missing = sorted(referenced - declared)
    unused = sorted(declared - referenced)
    errors: list[dict[str, Any]] = []
    if duplicate_names:
        errors.append({"code": "WM-ENV-001", "message": f"Duplicate contract variables: {duplicate_names}"})
    if missing:
        errors.append({"code": "WM-ENV-002", "message": f"Environment variables used but not declared: {missing}"})
    expected_example = render_env_example(contract)
    example_path = project_root / ".env.example"
    if not example_path.exists() or example_path.read_text(encoding="utf-8") != expected_example:
        errors.append({"code": "WM-ENV-003", "message": ".env.example is not synchronized with env-contract.json"})
    selected = Path(dotenv) if dotenv else project_root / ".env"
    values: dict[str, str] = {}
    if selected.exists():
        values = parse_dotenv(selected.read_text(encoding="utf-8"))
        unknown = sorted(set(values) - declared)
        if unknown:
            errors.append({"code": "WM-ENV-004", "message": f"Unknown variables in {selected}: {unknown}"})
        by_name = {item["name"]: item for item in contract["variables"]}
        for name, item in by_name.items():
            value = values.get(name, os.getenv(name, str(item.get("default", ""))))
            failure = _validate_value(item, value)
            if failure:
                errors.append({"code": "WM-ENV-005", "message": f"{name}: {failure}"})
    return {
        "schema": "wellm.env-check/v1",
        "ok": not errors,
        "contract": contract_path.as_posix(),
        "dotenv": selected.as_posix() if selected.exists() else None,
        "declared": len(declared),
        "referenced": len(referenced),
        "unused": unused,
        "errors": errors,
    }

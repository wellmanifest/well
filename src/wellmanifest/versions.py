from __future__ import annotations

import hashlib
from importlib.resources import files
import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .version import __version__

REGISTRY_SCHEMA = "wellm.version-registry/v1"
PROTOCOL_VERSION = "wellmanifest.protocol/v1"
IR_VERSION = "wellmanifest-ir/v1"


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _root_from_module() -> Path:
    return Path(__file__).resolve().parents[2]


def _contract_id(document: dict[str, Any], fallback: str) -> str:
    properties = document.get("properties", {})
    if isinstance(properties, dict):
        for key in ("schema", "spec"):
            entry = properties.get(key)
            if isinstance(entry, dict) and isinstance(entry.get("const"), str):
                return entry["const"]
    value = document.get("schema")
    if isinstance(value, str):
        return value
    return fallback


def _contract_version(contract: str, schema_id: str) -> tuple[str, str]:
    """Return the public contract version and compatibility policy.

    Schema contracts carrying `/vN` or `@N` use major compatibility. Schemas
    without a public major remain package-versioned and content-addressed.
    """

    for candidate in (contract, schema_id):
        match = re.search(r"(?:/v|@)([0-9]+)(?:$|[^0-9])", candidate)
        if match:
            return f"v{match.group(1)}", "exact-major"
    return __version__, "exact-hash"


def build_version_registry(root: str | Path | None = None) -> dict[str, Any]:
    from .dialects import DialectRegistry
    from .governance import available_profiles

    project_root = Path(root).resolve() if root else _root_from_module()
    schemas_dir = project_root / "schemas"
    dialects = []
    for item in DialectRegistry().describe():
        dialect_id = str(item["name"])
        family, _, version = dialect_id.partition("@")
        dialects.append(
            {
                "id": dialect_id,
                "family": family,
                "version": version or "unversioned",
                "status": "stable" if family in {"json", "yaml", "hcl", "proto3"} else "candidate",
                "documentKind": item["documentKind"],
                "mediaTypes": item["mediaTypes"],
                "extensions": item["extensions"],
            }
        )

    schema_entries: list[dict[str, Any]] = []
    if schemas_dir.exists():
        for path in sorted(schemas_dir.glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                continue
            Draft202012Validator.check_schema(document)
            schema_id = document.get("$id")
            if not isinstance(schema_id, str) or not schema_id:
                raise ValueError(f"JSON Schema is missing a versionable $id: {path}")
            contract = _contract_id(document, path.stem)
            version, compatibility = _contract_version(contract, schema_id)
            schema_entries.append(
                {
                    "path": path.relative_to(project_root).as_posix(),
                    "id": schema_id,
                    "contract": contract,
                    "version": version,
                    "compatibility": compatibility,
                    "dialect": "json-schema@2020-12",
                    "sha256": _sha256(path),
                }
            )

    api_entries: list[dict[str, Any]] = [
        {
            "id": "wellm-http-api",
            "version": "v1",
            "transport": "http",
            "basePath": "/v1",
            "contract": "openapi@3.1",
            "schemaPath": "schemas/openapi.json",
        },
        {
            "id": "wellm-websocket-api",
            "version": "v1",
            "transport": "websocket",
            "basePath": "/v1/ws",
            "contract": "asyncapi@3.0.0",
            "schemaPath": "schemas/asyncapi.yaml",
        },
        {
            "id": "wellm-mqtt-api",
            "version": "v1",
            "transport": "mqtt-v5",
            "basePath": "wellmanifest/v1/{tenant}",
            "contract": "asyncapi@3.0.0",
            "schemaPath": "schemas/asyncapi.yaml",
        },
        {
            "id": "wellm-grpc-api",
            "version": "v1",
            "transport": "grpc",
            "basePath": "wellmanifest.v1.RuntimeService",
            "contract": "proto3",
            "schemaPath": "proto/wellmanifest/v1/wellmanifest.proto",
        },
    ]
    for entry in api_entries:
        path = project_root / str(entry["schemaPath"])
        entry["sha256"] = _sha256(path) if path.exists() else None

    packages = [
        {"ecosystem": "python", "name": "wellm", "version": __version__},
        {"ecosystem": "npm", "name": "@wellmanifest/wellm-sdk", "version": __version__.replace("rc", "-rc.")},
        {"ecosystem": "cargo", "name": "wellmanifest-core", "version": __version__.replace("rc", "-rc.")},
        {"ecosystem": "container", "name": "wellmanifest/wellm", "version": __version__},
    ]

    registry = {
        "schema": REGISTRY_SCHEMA,
        "package": {"name": "wellm", "version": __version__},
        "protocols": [
            {"id": PROTOCOL_VERSION, "version": "1.0.0", "compatibility": "backward-compatible-within-v1"},
            {"id": IR_VERSION, "version": "1.0.0", "compatibility": "exact-major"},
            {"id": "wellm-governance-profile@1", "version": "1.0.0", "compatibility": "exact-major"},
            {"id": "wellm.type-module/v1", "version": "1.0.0", "compatibility": "exact-major"},
            {"id": "wellm.version-registry/v1", "version": "1.0.0", "compatibility": "exact-major"},
            {"id": "wellm.env-contract/v1", "version": "1.0.0", "compatibility": "exact-major"},
            {"id": "wellm.intent-format-project/v1", "version": "1.0.0", "compatibility": "exact-major"},
            {"id": "wellm.intent-format-analysis/v1", "version": "1.0.0", "compatibility": "exact-major"},
            {"id": "wellm.todo2code-format-evidence/v1", "version": "1.0.0", "compatibility": "exact-major"},
            {"id": "wellm.iot-telemetry/v1", "version": "1.0.0", "compatibility": "exact-major"},
            {"id": "wellm.iot-device-config/v1", "version": "1.0.0", "compatibility": "exact-major"},
        ],
        "standards": [
            {"id": "json@rfc8259", "version": "RFC 8259"},
            {"id": "yaml@1.2", "version": "1.2.2"},
            {"id": "json-schema@2020-12", "version": "2020-12"},
            {"id": "hcl@2", "version": "2"},
            {"id": "proto3", "version": "proto3"},
            {"id": "toon@1", "version": "1"},
            {"id": "mqtt", "version": "5.0"},
            {"id": "grpc", "version": "1"},
            {"id": "asyncapi", "version": "3.0.0"},
        ],
        "apis": api_entries,
        "dialects": sorted(dialects, key=lambda item: item["id"]),
        "formatProfiles": available_profiles(),
        "schemas": schema_entries,
        "packages": packages,
    }
    validate_version_registry(registry, project_root)
    return registry


def validate_version_registry(
    registry: dict[str, Any],
    root: str | Path | None = None,
    *,
    verify_files: bool = True,
) -> None:
    project_root = Path(root).resolve() if root else _root_from_module()
    schema_path = project_root / "schemas" / "version-registry.schema.json"
    if not schema_path.exists():
        schema_path = Path(__file__).resolve().parent / "resources" / "version-registry.schema.json"
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(registry)
    for collection in ("protocols", "standards", "apis", "dialects", "formatProfiles", "schemas", "packages"):
        values = registry.get(collection, [])
        identities = []
        for item in values:
            if collection == "schemas":
                identities.append(str(item.get("path")))
            elif collection == "packages":
                identities.append(f"{item.get('ecosystem')}:{item.get('name')}")
            else:
                identities.append(str(item.get("id")))
        duplicates = sorted({identity for identity in identities if identities.count(identity) > 1})
        if duplicates:
            raise ValueError(f"Duplicate {collection} version identities: {duplicates}")
    for api in registry.get("apis", []):
        if not api.get("sha256"):
            raise ValueError(f"API contract is unhashed: {api['id']}")
        if verify_files:
            schema_file = project_root / str(api["schemaPath"])
            if not schema_file.exists():
                raise ValueError(f"API contract is missing: {api['id']} -> {schema_file}")
    for dialect in registry.get("dialects", []):
        if "@" not in str(dialect.get("id", "")) and dialect.get("id") != "proto3":
            raise ValueError(f"Dialect identifier is not versioned: {dialect.get('id')}")
    for profile in registry.get("formatProfiles", []):
        if "@" not in str(profile.get("id", "")):
            raise ValueError(f"Format profile identifier is not versioned: {profile.get('id')}")


def serialize_registry(registry: dict[str, Any]) -> str:
    return json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def registry_paths(root: str | Path | None = None) -> tuple[Path, Path]:
    project_root = Path(root).resolve() if root else _root_from_module()
    return (
        project_root / "config" / "version-registry.json",
        project_root / "src" / "wellmanifest" / "resources" / "version-registry.json",
    )


def _load_packaged_registry() -> dict[str, Any] | None:
    try:
        resource = files("wellmanifest.resources").joinpath("version-registry.json")
        if resource.is_file():
            registry = json.loads(resource.read_text(encoding="utf-8"))
            validate_version_registry(registry, verify_files=False)
            return registry
    except (FileNotFoundError, ModuleNotFoundError, TypeError):
        return None
    return None


def sync_version_registry(root: str | Path | None = None, *, check: bool = False) -> dict[str, Any]:
    project_root = Path(root).resolve() if root else _root_from_module()
    source_checkout = (project_root / "schemas").is_dir() and (project_root / "config").is_dir()
    if check and not source_checkout:
        packaged = _load_packaged_registry()
        if packaged is None:
            raise ValueError("Packaged version registry is unavailable")
        return packaged

    registry = build_version_registry(project_root)
    rendered = serialize_registry(registry)
    paths = registry_paths(project_root)
    drift: list[str] = []
    for path in paths:
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != rendered:
                drift.append(path.as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8")
    if drift:
        raise ValueError("Version registry drift: " + ", ".join(drift))
    return registry


def load_version_registry(path: str | Path | None = None) -> dict[str, Any]:
    if path:
        registry = json.loads(Path(path).read_text(encoding="utf-8"))
        validate_version_registry(registry, Path(path).resolve().parent.parent, verify_files=False)
        return registry
    project, legacy_packaged_path = registry_paths()
    if project.exists():
        registry = json.loads(project.read_text(encoding="utf-8"))
        validate_version_registry(registry, verify_files=True)
        return registry
    packaged = _load_packaged_registry()
    if packaged is not None:
        return packaged
    if legacy_packaged_path.exists():
        registry = json.loads(legacy_packaged_path.read_text(encoding="utf-8"))
        validate_version_registry(registry, verify_files=False)
        return registry
    return build_version_registry()

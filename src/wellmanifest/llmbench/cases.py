from __future__ import annotations

import json
from typing import Any

from wellmanifest.models import Document, DocumentMetadata
from wellmanifest.runtime import WellManifestRuntime

from .models import BenchmarkCase


_FORMAT_GUIDANCE = {
    "json": "Return strict RFC 8259 JSON. No comments and no Markdown fence.",
    "yaml": "Return YAML 1.2 using only JSON-compatible values and string mapping keys.",
    "typed": "Return WellManifest typed@1 data syntax. Use blocks and `field = value`; do not add prose.",
    "hcl": "Return HCL-shaped WellManifest data with blocks and `field = value`; do not add prose.",
    "typescript": (
        "Return the safe WellManifest TypeScript data-module subset: `export default <JSON object> as const "
        "satisfies WellManifestDocument;`. Do not execute code or add functions."
    ),
}


def format_instruction(target_format: str) -> str:
    try:
        return _FORMAT_GUIDANCE[target_format]
    except KeyError as exc:
        raise ValueError(f"Unsupported benchmark target format: {target_format}") from exc


def infer_schema(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        schemas = [infer_schema(item) for item in value]
        item_schema = schemas[0] if schemas and all(schema == schemas[0] for schema in schemas) else {}
        return {"type": "array", "items": item_schema}
    if isinstance(value, dict):
        return {
            "type": "object",
            "additionalProperties": False,
            "required": list(value.keys()),
            "properties": {key: infer_schema(item) for key, item in value.items()},
        }
    return {}


def emit_expected(runtime: WellManifestRuntime, data: Any, target_format: str) -> str:
    document = Document(
        metadata=DocumentMetadata(source_dialect="json@rfc8259"),
        data=data,
        ir={"kind": "data", "value": data},
    )
    return runtime.registry.get(target_format).emit(document, projection="data", pretty=True)


def build_cases(
    fixture: dict[str, Any],
    formats: list[str],
    *,
    runtime: WellManifestRuntime | None = None,
) -> list[BenchmarkCase]:
    runtime = runtime or WellManifestRuntime()
    cases: list[BenchmarkCase] = []

    logic_examples: list[tuple[str, str, Any, Any, str]] = [
        (
            "project-roundtrip",
            "Preserve a deployment registry without changing any value",
            fixture,
            fixture,
            "roundtrip",
        ),
        (
            "uri-scope-logic",
            "Evaluate a concrete URI Process against wildcard permission scopes",
            {
                "uri": "plesk://host/site/command/sync",
                "allowed_uri_processes": ["plesk://host/site/*"],
                "rule": "A wildcard is a permission pattern and is never itself an executable URI.",
            },
            {
                "decision": {
                    "allowed": True,
                    "executable_uri": "plesk://host/site/command/sync",
                    "matched_scope": "plesk://host/site/*",
                    "wildcard_is_executable": False,
                }
            },
            "logic",
        ),
        (
            "publication-gate-logic",
            "Decide whether a Plesk publication may mutate after deterministic preflight",
            {
                "required_gates": ["subscription_can_create_domain", "dns_ready", "tls_ready"],
                "evidence": {
                    "subscription_can_create_domain": True,
                    "dns_ready": True,
                    "tls_ready": False,
                    "dry_run_plan_hash": "abc123",
                    "apply_plan_hash": "different456",
                    "signed_apply_grant": False,
                },
                "rule": "Mutation is fail-closed; every gate and a signed grant must be present.",
            },
            {
                "decision": {
                    "ready": False,
                    "mutation_allowed": False,
                    "blocked_gates": ["tls_ready", "plan_hash_match", "signed_apply_grant"],
                    "next_action": "plesk://host/site/command/ssl-ensure",
                }
            },
            "policy",
        ),
    ]

    for target_format in formats:
        if target_format not in _FORMAT_GUIDANCE:
            raise ValueError(f"Unsupported benchmark target format: {target_format}")
        for case_id, title, input_data, expected_data, category in logic_examples:
            schema = infer_schema(expected_data)
            prompt = _prompt(
                title=title,
                target_format=target_format,
                input_data=input_data,
                output_schema=schema,
            )
            cases.append(
                BenchmarkCase(
                    id=f"{case_id}:{target_format}",
                    title=title,
                    target_format=target_format,
                    input_data=input_data,
                    expected_data=expected_data,
                    output_schema=schema,
                    prompt=prompt,
                    weight=1.0 if category == "roundtrip" else 1.5,
                    category=category,
                )
            )
    return cases


def _prompt(*, title: str, target_format: str, input_data: Any, output_schema: dict[str, Any]) -> str:
    return "\n".join(
        [
            "You are taking a deterministic WellManifest format and logic capability test.",
            f"TASK: {title}",
            f"TARGET FORMAT: {target_format}",
            _FORMAT_GUIDANCE[target_format],
            "Return only the requested document. Do not wrap it in a Markdown code fence.",
            "INPUT (canonical JSON):",
            json.dumps(input_data, ensure_ascii=False, sort_keys=True, indent=2),
            "OUTPUT JSON SCHEMA (the target format must decode to data satisfying it):",
            json.dumps(output_schema, ensure_ascii=False, sort_keys=True, indent=2),
        ]
    )

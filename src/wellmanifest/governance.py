from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .dialects.policy import PolicyDialect
from .models import Diagnostic, Document, Severity, SourcePosition, SourceRange
from .source_maps import serialize_source_map

if TYPE_CHECKING:
    from .runtime import WellManifestRuntime


@dataclass(frozen=True)
class FormatProfile:
    id: str
    family: str
    media_type: str
    extension: str
    canonical: bool
    description: str


FORMAT_PROFILES: dict[str, FormatProfile] = {
    "wellm-typed@1": FormatProfile(
        "wellm-typed@1",
        "typed",
        "application/wellmanifest+typed",
        ".wm",
        True,
        "Canonical authoring profile with inline type metadata.",
    ),
    "json-data@1": FormatProfile(
        "json-data@1",
        "json",
        "application/json",
        ".json",
        False,
        "Readable JSON data preserving source object order.",
    ),
    "repo-json@1": FormatProfile(
        "repo-json@1",
        "json",
        "application/json",
        ".json",
        True,
        "Deterministic repository JSON ordered by schema and lexical dynamic keys.",
    ),
    "wire-json@1": FormatProfile(
        "wire-json@1",
        "json",
        "application/wellmanifest+json",
        ".json",
        True,
        "Compact deterministic JSON used for semantic digests and transport.",
    ),
    "yaml-json@1": FormatProfile(
        "yaml-json@1",
        "yaml",
        "application/wellmanifest+yaml",
        ".yaml",
        True,
        "YAML 1.2 restricted to the JSON-compatible data model.",
    ),
    "hcl-static@1": FormatProfile(
        "hcl-static@1",
        "hcl",
        "application/wellmanifest+hcl",
        ".hcl",
        True,
        "Static HCL-shaped data without evaluation-dependent expressions.",
    ),
    "typescript-data@1": FormatProfile(
        "typescript-data@1",
        "typescript",
        "application/wellmanifest+typescript",
        ".wm.ts",
        True,
        "Restricted export-default TypeScript data module.",
    ),
    "toon-map@1": FormatProfile(
        "toon-map@1",
        "toon",
        "application/wellmanifest+toon",
        ".toon.yaml",
        True,
        "YAML-compatible compact code/project map with versioned producer metadata.",
    ),
    "policy-md@1": FormatProfile(
        "policy-md@1",
        "policy",
        "text/markdown",
        ".md",
        True,
        "Markdown with canonical dsl/policy/wellm-policy fenced blocks.",
    ),
}


class GovernanceSourceSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    source: str
    target: str
    schema_ref: str | None = Field(default=None, alias="schema", serialization_alias="schema")
    source_dialect: str = Field(default="auto", alias="sourceDialect", serialization_alias="sourceDialect")
    profile: str = "repo-json@1"
    metadata: bool = True
    source_map: bool = Field(default=True, alias="sourceMap", serialization_alias="sourceMap")


class GovernancePolicySpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str
    ir_target: str | None = Field(default=None, alias="irTarget", serialization_alias="irTarget")
    canonical_fence: str = Field(default="wellm-policy", alias="canonicalFence", serialization_alias="canonicalFence")
    rewrite_fences: bool = Field(default=False, alias="rewriteFences", serialization_alias="rewriteFences")
    undeclared_states: Literal["error", "warning", "ignore"] = Field(
        default="error",
        alias="undeclaredStates",
        serialization_alias="undeclaredStates",
    )


class GovernanceProjectConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_id: Literal["wellm.governance-project/v1"] = Field(alias="schema", serialization_alias="schema")
    root: str = "."
    sources: list[GovernanceSourceSpec] = Field(default_factory=list)
    policies: list[GovernancePolicySpec] = Field(default_factory=list)
    checks: dict[str, Any] = Field(default_factory=dict)


class ArtifactBuildResult(BaseModel):
    id: str
    source: str
    target: str
    profile: str
    status: Literal["CREATED", "UPDATED", "CURRENT", "MISSING", "DRIFT", "INVALID", "SKIPPED"]
    semantic_sha256: str | None = None
    artifact_sha256: str | None = None
    metadata_target: str | None = None
    source_map_target: str | None = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class PolicyBuildResult(BaseModel):
    source: str
    status: Literal["CURRENT", "UPDATED", "INVALID"]
    rule_count: int = 0
    state_count: int = 0
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class GovernanceBuildReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_id: Literal["wellm.governance-build-report/v1"] = Field(
        default="wellm.governance-build-report/v1", alias="schema", serialization_alias="schema"
    )
    mode: Literal["build", "check"]
    ok: bool
    project: str
    artifacts: list[ArtifactBuildResult] = Field(default_factory=list)
    policies: list[PolicyBuildResult] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class SemanticChange(BaseModel):
    classification: Literal["BREAKING", "NON_BREAKING", "CHANGED", "INFO"]
    operation: Literal["add", "remove", "replace", "reorder", "type-change"]
    path: str
    before: Any = None
    after: Any = None
    message: str


class SemanticDiffReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_id: Literal["wellm.semantic-diff/v1"] = Field(
        default="wellm.semantic-diff/v1", alias="schema", serialization_alias="schema"
    )
    equivalent: bool
    left_digest: str = Field(alias="leftDigest", serialization_alias="leftDigest")
    right_digest: str = Field(alias="rightDigest", serialization_alias="rightDigest")
    changes: list[SemanticChange] = Field(default_factory=list)


class RoundtripStep(BaseModel):
    dialect: str
    semantic_sha256: str
    equivalent_to_source: bool
    lossiness: Literal["LOSSLESS", "NORMALIZED", "LOSSY", "UNSUPPORTED"]
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class RoundtripReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_id: Literal["wellm.conversion-report/v1"] = Field(
        default="wellm.conversion-report/v1", alias="schema", serialization_alias="schema"
    )
    source_dialect: str
    source_semantic_sha256: str
    equivalent: bool
    steps: list[RoundtripStep] = Field(default_factory=list)
    preserved: list[str] = Field(default_factory=lambda: ["values", "object keys", "array order", "nullability"])
    discarded: list[str] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


def available_profiles() -> list[dict[str, Any]]:
    return [
        {
            "id": profile.id,
            "family": profile.family,
            "mediaType": profile.media_type,
            "extension": profile.extension,
            "canonical": profile.canonical,
            "description": profile.description,
        }
        for profile in FORMAT_PROFILES.values()
    ]


def normalize_json_value(value: Any, *, path: str = "$") -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Non-finite number at {path} is not valid in Wellm JSON profiles")
        if value == 0:
            return 0
        if value.is_integer():
            return int(value)
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [normalize_json_value(item, path=f"{path}/{index}") for index, item in enumerate(value)]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"Object key at {path} must be a string, got {type(key).__name__}")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in result:
                raise ValueError(f"Unicode normalization creates duplicate key {normalized_key!r} at {path}")
            result[normalized_key] = normalize_json_value(item, path=f"{path}/{_escape(normalized_key)}")
        return result
    raise ValueError(f"Value at {path} is not JSON-compatible: {type(value).__name__}")


def semantic_bytes(value: Any) -> bytes:
    normalized = normalize_json_value(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def semantic_sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(semantic_bytes(value)).hexdigest()


def artifact_sha256(content: bytes | str) -> str:
    raw = content.encode("utf-8") if isinstance(content, str) else content
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def serialize_profile(
    value: Any,
    profile: str,
    *,
    schema: dict[str, Any] | None = None,
) -> str:
    if profile not in FORMAT_PROFILES:
        raise KeyError(f"Unknown format profile: {profile}")
    normalized = normalize_json_value(value)
    if profile == "json-data@1":
        return json.dumps(normalized, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if profile == "repo-json@1":
        ordered = order_by_schema(normalized, schema)
        return json.dumps(ordered, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if profile == "wire-json@1":
        return semantic_bytes(normalized).decode("utf-8") + "\n"
    if profile == "yaml-json@1":
        ordered = order_by_schema(normalized, schema)
        return yaml.safe_dump(
            ordered,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=1000,
        )
    if profile == "typescript-data@1":
        rendered = json.dumps(order_by_schema(normalized, schema), ensure_ascii=False, indent=2, allow_nan=False)
        return (
            "// Generated by wellm. This module contains data only.\n"
            "export type WellManifestDocument = Readonly<Record<string, unknown>> | readonly unknown[];\n\n"
            f"export default {rendered} as const satisfies WellManifestDocument;\n"
        )
    if profile == "toon-map@1":
        ordered = order_by_schema(normalized, schema)
        return (
            "# producer: wellm | artifact: manifest.toon.yaml | schema: 1\n"
            + yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False, default_flow_style=False, width=1000)
        )
    raise ValueError(f"Profile {profile} is emitted through its dialect runtime, not serialize_profile()")


def order_by_schema(value: Any, schema: dict[str, Any] | None) -> Any:
    normalized = normalize_json_value(value)
    if schema is None:
        return _order_lexical(normalized)
    return _order_with_schema(normalized, schema, schema)


def artifact_metadata(
    *,
    source: str,
    target: str,
    source_dialect: str,
    target_profile: str,
    schema_ref: str | None,
    source_bytes: bytes,
    artifact_bytes: bytes,
    value: Any,
    schema_bytes: bytes | None = None,
    generator_version: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "wellm.artifact-metadata/v1",
        "source": source,
        "target": target,
        "sourceDialect": source_dialect,
        "targetProfile": target_profile,
        "schemaRef": schema_ref,
        "generator": {"name": "wellm", "version": generator_version},
        "sourceSha256": artifact_sha256(source_bytes),
        "semanticSha256": semantic_sha256(value),
        "artifactSha256": artifact_sha256(artifact_bytes),
    }
    if schema_bytes is not None:
        result["schemaSha256"] = artifact_sha256(schema_bytes)
    return result


def lint_policy_document(
    document: Document,
    *,
    undeclared_states: Literal["error", "warning", "ignore"] = "error",
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    rules = document.ir.get("rules", [])
    states = document.ir.get("states", [])
    transitions = document.ir.get("transitions", [])

    seen_rules: dict[str, int] = {}
    for rule in rules:
        rule_id = str(rule.get("id", ""))
        line = int(rule.get("sourceLine", 1))
        if rule_id in seen_rules:
            diagnostics.append(
                _policy_diagnostic(
                    "WM-POLICY-201",
                    Severity.ERROR,
                    f"Duplicate rule identifier {rule_id!r}; first declared on line {seen_rules[rule_id]}.",
                    document,
                    line,
                )
            )
        else:
            seen_rules[rule_id] = line

    seen_states: set[str] = set()
    for state in states:
        if state in seen_states:
            diagnostics.append(
                _policy_diagnostic(
                    "WM-POLICY-202",
                    Severity.ERROR,
                    f"Duplicate state declaration {state!r}.",
                    document,
                    1,
                )
            )
        seen_states.add(state)

    if undeclared_states != "ignore":
        severity = Severity.ERROR if undeclared_states == "error" else Severity.WARNING
        for transition in transitions:
            line = int(transition.get("sourceLine", 1))
            source_state = str(transition.get("from", ""))
            target_state = str(transition.get("to", ""))
            if source_state != "ANY" and source_state not in seen_states:
                diagnostics.append(
                    _policy_diagnostic(
                        "WM-POLICY-203",
                        severity,
                        f"Transition source {source_state!r} is not declared in this state machine.",
                        document,
                        line,
                    )
                )
            if target_state not in seen_states:
                diagnostics.append(
                    _policy_diagnostic(
                        "WM-POLICY-204",
                        severity,
                        f"Transition target {target_state!r} is not declared in this state machine.",
                        document,
                        line,
                    )
                )
        for rule in rules:
            for next_expression in rule.get("next", []):
                for target in _next_targets(str(next_expression)):
                    if target not in seen_states:
                        diagnostics.append(
                            _policy_diagnostic(
                                "WM-POLICY-205",
                                severity,
                                f"Rule {rule.get('id')!r} references undeclared NEXT state {target!r}.",
                                document,
                                int(rule.get("sourceLine", 1)),
                            )
                        )
    return diagnostics


def semantic_diff(left: Any, right: Any) -> SemanticDiffReport:
    left_normalized = normalize_json_value(left)
    right_normalized = normalize_json_value(right)
    changes: list[SemanticChange] = []
    _diff_value(left_normalized, right_normalized, "", changes)
    return SemanticDiffReport(
        equivalent=not changes,
        leftDigest=semantic_sha256(left_normalized),
        rightDigest=semantic_sha256(right_normalized),
        changes=changes,
    )


def format_semantic_diff(report: SemanticDiffReport) -> str:
    if report.equivalent:
        return f"EQUIVALENT {report.left_digest}\n"
    lines = [
        f"left:  {report.left_digest}",
        f"right: {report.right_digest}",
        "",
    ]
    for change in report.changes:
        lines.append(f"{change.classification} {change.operation.upper()} {change.path or '/'}: {change.message}")
    return "\n".join(lines) + "\n"


def roundtrip_document(
    runtime: WellManifestRuntime,
    document: Document,
    dialects: list[str],
    *,
    schema: dict[str, Any] | None = None,
) -> RoundtripReport:
    if document.data is None:
        raise ValueError("Round-trip data projection requires a document with data")
    source_digest = semantic_sha256(document.data)
    current = document
    steps: list[RoundtripStep] = []
    report_diagnostics: list[Diagnostic] = []
    discarded: set[str] = set()
    for dialect_name in dialects:
        try:
            target = runtime.registry.get(dialect_name)
            output = target.emit(current, projection="data", pretty=True)
            reparsed = target.parse(output, source_name=f"<roundtrip:{target.name}>")
            diagnostics = list(reparsed.diagnostics)
            if schema is not None:
                diagnostics.extend(
                    runtime.schema_validator.validate(
                        reparsed.data,
                        schema,
                        source=f"<roundtrip:{target.name}>",
                        source_map=reparsed.source_map,
                    )
                )
            digest = semantic_sha256(reparsed.data)
            equivalent = digest == source_digest
            if target.name in {"hcl@2", "json@rfc8259", "yaml@1.2/json-compatible", "typescript@wellm-1"}:
                discarded.update({"comments", "source whitespace", "inline type spelling"})
            steps.append(
                RoundtripStep(
                    dialect=target.name,
                    semantic_sha256=digest,
                    equivalent_to_source=equivalent,
                    lossiness="NORMALIZED" if equivalent else "LOSSY",
                    diagnostics=diagnostics,
                )
            )
            report_diagnostics.extend(diagnostics)
            current = reparsed
        except Exception as exc:
            diagnostic = Diagnostic(
                code="WM-ROUNDTRIP-001",
                severity=Severity.ERROR,
                phase="convert",
                dialect=dialect_name,
                message=str(exc),
            )
            steps.append(
                RoundtripStep(
                    dialect=dialect_name,
                    semantic_sha256="",
                    equivalent_to_source=False,
                    lossiness="UNSUPPORTED",
                    diagnostics=[diagnostic],
                )
            )
            report_diagnostics.append(diagnostic)
            break
    equivalent = bool(steps) and all(step.equivalent_to_source for step in steps)
    return RoundtripReport(
        source_dialect=document.metadata.source_dialect,
        source_semantic_sha256=source_digest,
        equivalent=equivalent,
        steps=steps,
        discarded=sorted(discarded),
        diagnostics=report_diagnostics,
    )


class GovernanceBuilder:
    def __init__(self, runtime: WellManifestRuntime):
        self.runtime = runtime

    def load_config(self, path: str | Path) -> GovernanceProjectConfig:
        config_path = Path(path)
        text = config_path.read_text(encoding="utf-8")
        if config_path.suffix.lower() == ".json":
            value = json.loads(text)
        else:
            value = yaml.safe_load(text)
        return GovernanceProjectConfig.model_validate(value)

    def build(self, path: str | Path, *, check: bool = False) -> GovernanceBuildReport:
        config_path = Path(path).resolve()
        config = self.load_config(config_path)
        project_root = (config_path.parent / config.root).resolve()
        artifacts: list[ArtifactBuildResult] = []
        policy_results: list[PolicyBuildResult] = []
        all_diagnostics: list[Diagnostic] = []

        for spec in config.sources:
            result = self._build_source(spec, project_root=project_root, check=check)
            artifacts.append(result)
            all_diagnostics.extend(result.diagnostics)

        for spec in config.policies:
            result = self._build_policy(spec, project_root=project_root, check=check)
            policy_results.append(result)
            all_diagnostics.extend(result.diagnostics)

        drift_statuses = {"MISSING", "DRIFT", "INVALID"}
        ok = not any(item.severity == Severity.ERROR for item in all_diagnostics)
        if check and any(item.status in drift_statuses for item in artifacts):
            ok = False
        if any(item.status == "INVALID" for item in policy_results):
            ok = False
        return GovernanceBuildReport(
            mode="check" if check else "build",
            ok=ok,
            project=str(config_path),
            artifacts=artifacts,
            policies=policy_results,
            diagnostics=all_diagnostics,
        )

    def _build_source(
        self,
        spec: GovernanceSourceSpec,
        *,
        project_root: Path,
        check: bool,
    ) -> ArtifactBuildResult:
        source_path = _resolve_path(project_root, spec.source)
        target_path = _resolve_target(project_root, spec.target)
        source_bytes = source_path.read_bytes()
        source_text = source_bytes.decode("utf-8")
        document = self.runtime.parse(source_text, dialect=spec.source_dialect, source_name=str(source_path))
        diagnostics = list(document.diagnostics)

        schema: dict[str, Any] | None = None
        schema_bytes: bytes | None = None
        schema_path: Path | None = None
        if spec.schema_ref:
            schema_path = _resolve_path(project_root, spec.schema_ref)
            schema_bytes = schema_path.read_bytes()
            schema = json.loads(schema_bytes)
            diagnostics.extend(
                self.runtime.schema_validator.validate(
                    document.data,
                    schema,
                    source=str(source_path),
                    source_map=document.source_map,
                )
            )

        artifact_id = spec.id or target_path.name
        if any(item.severity == Severity.ERROR for item in diagnostics):
            return ArtifactBuildResult(
                id=artifact_id,
                source=str(source_path),
                target=str(target_path),
                profile=spec.profile,
                status="INVALID",
                semantic_sha256=semantic_sha256(document.data),
                diagnostics=diagnostics,
            )

        if spec.profile in {"repo-json@1", "json-data@1", "wire-json@1", "yaml-json@1", "typescript-data@1"}:
            rendered = serialize_profile(document.data, spec.profile, schema=schema)
        else:
            dialect_map = {
                "wellm-typed@1": "typed",
                "hcl-static@1": "hcl",
            }
            target_dialect = dialect_map.get(spec.profile)
            if target_dialect is None:
                raise ValueError(f"Unsupported governance output profile: {spec.profile}")
            rendered = self.runtime.registry.get(target_dialect).emit(document, projection="data", pretty=True)
        artifact_bytes = rendered.encode("utf-8")
        existing = target_path.read_bytes() if target_path.exists() else None
        if existing == artifact_bytes:
            status: Literal["CREATED", "UPDATED", "CURRENT", "MISSING", "DRIFT", "INVALID", "SKIPPED"] = "CURRENT"
        elif check:
            status = "MISSING" if existing is None else "DRIFT"
            diagnostics.append(
                Diagnostic(
                    code="WM-GOV-101" if existing is None else "WM-GOV-102",
                    severity=Severity.ERROR,
                    phase="governance",
                    source=str(target_path),
                    message=(
                        "Generated governance artifact is missing."
                        if existing is None
                        else "Generated governance artifact differs from its Wellm source."
                    ),
                    hint=f"Run `wellm governance build {project_root}` without --check.",
                )
            )
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(artifact_bytes)
            status = "CREATED" if existing is None else "UPDATED"

        metadata_target: Path | None = None
        source_map_target: Path | None = None
        if not check or status == "CURRENT":
            if spec.metadata:
                metadata_target = target_path.with_name(target_path.name + ".wellm-meta.json")
                metadata_value = artifact_metadata(
                    source=_relative_or_absolute(source_path, project_root),
                    target=_relative_or_absolute(target_path, project_root),
                    source_dialect=document.metadata.source_dialect,
                    target_profile=spec.profile,
                    schema_ref=_relative_or_absolute(schema_path, project_root) if schema_path else None,
                    source_bytes=source_bytes,
                    artifact_bytes=artifact_bytes,
                    value=document.data,
                    schema_bytes=schema_bytes,
                    generator_version=self.runtime.version,
                )
                metadata_bytes = serialize_profile(metadata_value, "repo-json@1").encode("utf-8")
                self._write_or_check_sidecar(metadata_target, metadata_bytes, check, diagnostics)
            if spec.source_map:
                source_map_target = target_path.with_name(target_path.name + ".wellm-map.json")
                source_map_value = serialize_source_map(
                    document.source_map,
                    source=_relative_or_absolute(source_path, project_root),
                    generated=_relative_or_absolute(target_path, project_root),
                )
                source_map_bytes = serialize_profile(source_map_value, "repo-json@1").encode("utf-8")
                self._write_or_check_sidecar(source_map_target, source_map_bytes, check, diagnostics)

        return ArtifactBuildResult(
            id=artifact_id,
            source=str(source_path),
            target=str(target_path),
            profile=spec.profile,
            status=status,
            semantic_sha256=semantic_sha256(document.data),
            artifact_sha256=artifact_sha256(artifact_bytes),
            metadata_target=str(metadata_target) if metadata_target else None,
            source_map_target=str(source_map_target) if source_map_target else None,
            diagnostics=diagnostics,
        )

    def _write_or_check_sidecar(
        self,
        path: Path,
        expected: bytes,
        check: bool,
        diagnostics: list[Diagnostic],
    ) -> None:
        existing = path.read_bytes() if path.exists() else None
        if existing == expected:
            return
        if check:
            diagnostics.append(
                Diagnostic(
                    code="WM-GOV-103",
                    severity=Severity.ERROR,
                    phase="governance",
                    source=str(path),
                    message="Generated Wellm sidecar is missing or stale.",
                )
            )
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(expected)

    def _build_policy(
        self,
        spec: GovernancePolicySpec,
        *,
        project_root: Path,
        check: bool,
    ) -> PolicyBuildResult:
        source_path = _resolve_path(project_root, spec.source)
        source = source_path.read_text(encoding="utf-8")
        document = self.runtime.parse(source, dialect="policy", source_name=str(source_path))
        diagnostics = [*document.diagnostics, *lint_policy_document(document, undeclared_states=spec.undeclared_states)]
        changed = False
        if spec.rewrite_fences:
            rewritten, count = PolicyDialect.rewrite_fences(source, target=spec.canonical_fence)
            if count:
                changed = True
                if check:
                    diagnostics.append(
                        Diagnostic(
                            code="WM-POLICY-102",
                            severity=Severity.ERROR,
                            phase="format",
                            source=str(source_path),
                            message=f"{count} policy-shaped compatibility fence(s) require canonical formatting.",
                        )
                    )
                else:
                    source_path.write_text(rewritten, encoding="utf-8")
        if spec.ir_target:
            target = _resolve_target(project_root, spec.ir_target)
            rendered = serialize_profile(document.ir, "repo-json@1")
            expected = rendered.encode("utf-8")
            current = target.read_bytes() if target.exists() else None
            if current != expected:
                changed = True
                if check:
                    diagnostics.append(
                        Diagnostic(
                            code="WM-POLICY-103",
                            severity=Severity.ERROR,
                            phase="governance",
                            source=str(target),
                            message="Generated policy IR is missing or stale.",
                        )
                    )
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(expected)
        invalid = any(item.severity == Severity.ERROR for item in diagnostics)
        return PolicyBuildResult(
            source=str(source_path),
            status="INVALID" if invalid else ("UPDATED" if changed and not check else "CURRENT"),
            rule_count=len(document.ir.get("rules", [])),
            state_count=len(document.ir.get("states", [])),
            diagnostics=diagnostics,
        )


def _order_lexical(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _order_lexical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_order_lexical(item) for item in value]
    return value


def _order_with_schema(value: Any, schema: dict[str, Any], root: dict[str, Any]) -> Any:
    schema = _select_schema(value, _resolve_schema(schema, root), root)
    if isinstance(value, dict):
        properties = _merged_properties(schema, root)
        ordered_keys = [key for key in properties if key in value]
        ordered_keys.extend(sorted(key for key in value if key not in properties))
        result: dict[str, Any] = {}
        additional = schema.get("additionalProperties") if isinstance(schema, dict) else None
        for key in ordered_keys:
            child_schema = properties.get(key)
            if child_schema is None and isinstance(additional, dict):
                child_schema = additional
            result[key] = _order_with_schema(value[key], child_schema or {}, root)
        return result
    if isinstance(value, list):
        prefix = schema.get("prefixItems", []) if isinstance(schema, dict) else []
        items = schema.get("items", {}) if isinstance(schema, dict) else {}
        return [
            _order_with_schema(item, prefix[index] if index < len(prefix) else (items if isinstance(items, dict) else {}), root)
            for index, item in enumerate(value)
        ]
    return value


def _resolve_schema(schema: Any, root: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/"):
        current: Any = root
        for part in reference[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, dict) or part not in current:
                return schema
            current = current[part]
        if isinstance(current, dict):
            return {**current, **{key: value for key, value in schema.items() if key != "$ref"}}
    return schema


def _select_schema(value: Any, schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    for keyword in ("oneOf", "anyOf"):
        options = schema.get(keyword)
        if isinstance(options, list):
            for option in options:
                candidate = _resolve_schema(option, root)
                if _schema_matches_shallow(value, candidate):
                    return {**schema, **candidate}
    return schema


def _schema_matches_shallow(value: Any, schema: dict[str, Any]) -> bool:
    expected_type = schema.get("type")
    if expected_type == "null" and value is not None:
        return False
    if expected_type == "object" and not isinstance(value, dict):
        return False
    if expected_type == "array" and not isinstance(value, list):
        return False
    if expected_type == "string" and not isinstance(value, str):
        return False
    if "const" in schema and value != schema["const"]:
        return False
    if isinstance(value, dict):
        for key, child in schema.get("properties", {}).items():
            if key in value and isinstance(child, dict) and "const" in child and value[key] != child["const"]:
                return False
    return True


def _merged_properties(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if isinstance(schema.get("properties"), dict):
        result.update(schema["properties"])
    for item in schema.get("allOf", []) if isinstance(schema.get("allOf"), list) else []:
        resolved = _resolve_schema(item, root)
        if isinstance(resolved.get("properties"), dict):
            result.update(resolved["properties"])
    return result


def _diff_value(left: Any, right: Any, path: str, changes: list[SemanticChange]) -> None:
    if type(left) is not type(right):
        changes.append(
            SemanticChange(
                classification="BREAKING",
                operation="type-change",
                path=path,
                before=left,
                after=right,
                message=f"Type changed from {type(left).__name__} to {type(right).__name__}.",
            )
        )
        return
    if isinstance(left, dict):
        for key in sorted(left.keys() - right.keys()):
            child = f"{path}/{_escape(key)}"
            changes.append(
                SemanticChange(
                    classification="BREAKING",
                    operation="remove",
                    path=child,
                    before=left[key],
                    message=f"Removed property {key!r}.",
                )
            )
        for key in sorted(right.keys() - left.keys()):
            child = f"{path}/{_escape(key)}"
            changes.append(
                SemanticChange(
                    classification="NON_BREAKING",
                    operation="add",
                    path=child,
                    after=right[key],
                    message=f"Added property {key!r}.",
                )
            )
        for key in sorted(left.keys() & right.keys()):
            _diff_value(left[key], right[key], f"{path}/{_escape(key)}", changes)
        return
    if isinstance(left, list):
        if _all_scalars(left) and _all_scalars(right):
            left_keys = {_scalar_key(item): item for item in left}
            right_keys = {_scalar_key(item): item for item in right}
            for key in sorted(left_keys.keys() - right_keys.keys()):
                changes.append(
                    SemanticChange(
                        classification="BREAKING",
                        operation="remove",
                        path=path,
                        before=left_keys[key],
                        message=f"Removed list value {left_keys[key]!r}.",
                    )
                )
            for key in sorted(right_keys.keys() - left_keys.keys()):
                changes.append(
                    SemanticChange(
                        classification="NON_BREAKING",
                        operation="add",
                        path=path,
                        after=right_keys[key],
                        message=f"Added list value {right_keys[key]!r}.",
                    )
                )
            if not (left_keys.keys() ^ right_keys.keys()) and left != right:
                changes.append(
                    SemanticChange(
                        classification="CHANGED",
                        operation="reorder",
                        path=path,
                        before=left,
                        after=right,
                        message="List values are equal but their order changed.",
                    )
                )
            return
        common = min(len(left), len(right))
        for index in range(common):
            _diff_value(left[index], right[index], f"{path}/{index}", changes)
        for index in range(common, len(left)):
            changes.append(
                SemanticChange(
                    classification="BREAKING",
                    operation="remove",
                    path=f"{path}/{index}",
                    before=left[index],
                    message="Removed list item.",
                )
            )
        for index in range(common, len(right)):
            changes.append(
                SemanticChange(
                    classification="NON_BREAKING",
                    operation="add",
                    path=f"{path}/{index}",
                    after=right[index],
                    message="Added list item.",
                )
            )
        return
    if left != right:
        changes.append(
            SemanticChange(
                classification="CHANGED",
                operation="replace",
                path=path,
                before=left,
                after=right,
                message=f"Value changed from {left!r} to {right!r}.",
            )
        )


def _policy_diagnostic(
    code: str,
    severity: Severity,
    message: str,
    document: Document,
    line: int,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        phase="policy-lint",
        dialect=document.metadata.source_dialect,
        source=document.metadata.source_name,
        message=message,
        range=SourceRange(
            start=SourcePosition(line=line, column=1),
            end=SourcePosition(line=line, column=2),
        ),
    )


def _next_targets(expression: str) -> list[str]:
    result: list[str] = []
    for part in re.split(r"\s+OR\s+", expression, flags=re.IGNORECASE):
        match = re.match(r"\s*([A-Z][A-Z0-9_]*)\b", part)
        if match:
            result.append(match.group(1))
    return result


def _all_scalars(values: list[Any]) -> bool:
    return all(item is None or isinstance(item, (str, int, float, bool)) for item in values)


def _scalar_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _resolve_path(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()


def _resolve_target(root: Path, value: str) -> Path:
    target = _resolve_path(root, value)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Governance target {target} escapes project root {root}") from exc
    return target


def _relative_or_absolute(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")

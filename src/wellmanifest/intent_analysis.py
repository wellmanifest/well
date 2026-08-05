from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .governance import semantic_diff, semantic_sha256
from .models import Diagnostic, Severity

if TYPE_CHECKING:
    from .runtime import WellManifestRuntime


class IntentRepresentationSpec(BaseModel):
    id: str
    path: str
    dialect: str = "auto"
    role: str = "representation"


class IntentFormatProject(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_id: str = Field(alias="schema", serialization_alias="schema")
    id: str
    schema_ref: str | None = Field(default=None, alias="schemaRef", serialization_alias="schemaRef")
    representations: list[IntentRepresentationSpec]
    preferred_authoring: list[str] = Field(
        default_factory=lambda: ["typed@1", "json@rfc8259", "yaml@1.2/json-compatible", "typescript@wellm-1"],
        alias="preferredAuthoring",
        serialization_alias="preferredAuthoring",
    )


class RepresentationResult(BaseModel):
    id: str
    path: str
    requested_dialect: str
    detected_dialect: str | None = None
    artifact_sha256: str
    semantic_sha256: str | None = None
    schema_valid: bool | None = None
    type_hints: dict[str, str] = Field(default_factory=dict)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    normalized: Any = None


class PairwiseResult(BaseModel):
    left: str
    right: str
    equivalent: bool
    change_count: int
    changes: list[dict[str, Any]] = Field(default_factory=list)


class IntentFormatAnalysis(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_id: str = Field(
        default="wellm.intent-format-analysis/v1", alias="schema", serialization_alias="schema"
    )
    id: str
    source_project: str | None = Field(default=None, alias="sourceProject", serialization_alias="sourceProject")
    equivalent: bool
    canonical_semantic_sha256: str | None = Field(
        default=None, alias="canonicalSemanticSha256", serialization_alias="canonicalSemanticSha256"
    )
    recommended_authoring: str | None = Field(
        default=None, alias="recommendedAuthoring", serialization_alias="recommendedAuthoring"
    )
    recommended_enforcement: str = Field(
        default="json@rfc8259", alias="recommendedEnforcement", serialization_alias="recommendedEnforcement"
    )
    representations: list[RepresentationResult] = Field(default_factory=list)
    pairs: list[PairwiseResult] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    todo2code: dict[str, Any] = Field(default_factory=dict)


class InlineIntentAnalysisRequest(BaseModel):
    id: str = "inline-intent-analysis"
    schema_document: dict[str, Any] | None = Field(default=None, alias="schema", serialization_alias="schema")
    representations: list[dict[str, Any]]


def _artifact_sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_project_member(base: Path, value: str, *, label: str) -> Path:
    """Resolve a project member without allowing reads outside the project directory."""
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError(f"{label} must be a relative path: {value}")
    resolved = (base / candidate).resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"{label} escapes the project directory: {value}") from exc
    return resolved


def _load_object(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    value = yaml.safe_load(text) if path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def _preferred_result(results: list[RepresentationResult], preferred: list[str]) -> str | None:
    valid = [item for item in results if item.semantic_sha256 and not any(d.severity == Severity.ERROR for d in item.diagnostics)]
    for dialect in preferred:
        for item in valid:
            if item.detected_dialect == dialect or item.requested_dialect == dialect:
                return item.id
    return valid[0].id if valid else None


def analyze_inline_representations(
    runtime: WellManifestRuntime,
    request: InlineIntentAnalysisRequest | dict[str, Any],
) -> IntentFormatAnalysis:
    request = request if isinstance(request, InlineIntentAnalysisRequest) else InlineIntentAnalysisRequest.model_validate(request)
    results: list[RepresentationResult] = []
    diagnostics: list[Diagnostic] = []
    for index, item in enumerate(request.representations):
        representation_id = str(item.get("id", f"representation-{index + 1}"))
        source = item.get("source")
        dialect = str(item.get("dialect", "auto"))
        source_name = str(item.get("sourceName", representation_id))
        if not isinstance(source, str):
            diagnostic = Diagnostic(
                code="WM-INTENT-001",
                severity=Severity.ERROR,
                phase="intent-analysis",
                source=source_name,
                message="Representation source must be text.",
            )
            diagnostics.append(diagnostic)
            results.append(
                RepresentationResult(
                    id=representation_id,
                    path=source_name,
                    requested_dialect=dialect,
                    artifact_sha256=_artifact_sha256(""),
                    diagnostics=[diagnostic],
                )
            )
            continue
        try:
            document = runtime.parse(source, dialect=dialect, source_name=source_name)
            item_diagnostics = list(document.diagnostics)
            schema_valid: bool | None = None
            if request.schema_document is not None:
                validation = runtime.schema_validator.validate(
                    document.data,
                    request.schema_document,
                    source=source_name,
                    source_map=document.source_map,
                )
                item_diagnostics.extend(validation)
                schema_valid = not any(entry.severity == Severity.ERROR for entry in validation)
            result = RepresentationResult(
                id=representation_id,
                path=source_name,
                requested_dialect=dialect,
                detected_dialect=document.metadata.source_dialect,
                artifact_sha256=_artifact_sha256(source),
                semantic_sha256=semantic_sha256(document.data),
                schema_valid=schema_valid,
                type_hints=document.metadata.type_hints,
                diagnostics=item_diagnostics,
                normalized=document.data,
            )
            results.append(result)
            diagnostics.extend(item_diagnostics)
        except Exception as exc:  # parser adapters normalize errors into diagnostics here
            diagnostic = Diagnostic(
                code="WM-INTENT-002",
                severity=Severity.ERROR,
                phase="intent-analysis",
                dialect=dialect,
                source=source_name,
                message=str(exc),
            )
            diagnostics.append(diagnostic)
            results.append(
                RepresentationResult(
                    id=representation_id,
                    path=source_name,
                    requested_dialect=dialect,
                    artifact_sha256=_artifact_sha256(source),
                    diagnostics=[diagnostic],
                )
            )

    pairs: list[PairwiseResult] = []
    comparable = [item for item in results if item.semantic_sha256 is not None]
    for left_index, left in enumerate(comparable):
        for right in comparable[left_index + 1 :]:
            comparison = semantic_diff(left.normalized, right.normalized)
            pairs.append(
                PairwiseResult(
                    left=left.id,
                    right=right.id,
                    equivalent=comparison.equivalent,
                    change_count=len(comparison.changes),
                    changes=[item.model_dump(mode="json") for item in comparison.changes],
                )
            )
    semantic_hashes = {item.semantic_sha256 for item in comparable if item.semantic_sha256}
    equivalent = bool(comparable) and len(semantic_hashes) == 1 and not any(
        item.severity == Severity.ERROR for item in diagnostics
    )
    if not equivalent:
        diagnostics.append(
            Diagnostic(
                code="WM-INTENT-DRIFT-001",
                severity=Severity.ERROR,
                phase="intent-analysis",
                message="Intent representations are not all schema-valid and semantically equivalent.",
                hint="Review pairwise changes before accepting or generating implementation scope.",
            )
        )
    else:
        diagnostics.append(
            Diagnostic(
                code="WM-INTENT-100",
                severity=Severity.INFO,
                phase="intent-analysis",
                message="All intent representations normalize to the same semantic value.",
            )
        )
    preferred = _preferred_result(
        results,
        ["typed@1", "json@rfc8259", "yaml@1.2/json-compatible", "typescript@wellm-1", "hcl@2", "toon@1"],
    )
    return IntentFormatAnalysis(
        id=request.id,
        equivalent=equivalent,
        canonical_semantic_sha256=next(iter(semantic_hashes)) if len(semantic_hashes) == 1 else None,
        recommended_authoring=preferred,
        representations=results,
        pairs=pairs,
        diagnostics=diagnostics,
        todo2code={
            "evidenceContract": "wellm.todo2code-format-evidence/v1",
            "recommendedActions": ["extract_config", "link", "diagnose", "diff", "compare_workspace"],
            "reason": "Use Wellm semantic equivalence as deterministic evidence; let todo2code link it with Git, AST, TODO and documentation evidence.",
        },
    )


def analyze_intent_project(
    runtime: WellManifestRuntime,
    project_path: str | Path,
) -> IntentFormatAnalysis:
    path = Path(project_path).resolve()
    value = _load_object(path)
    project = IntentFormatProject.model_validate(value)
    if project.schema_id != "wellm.intent-format-project/v1":
        raise ValueError(f"Unsupported intent project schema: {project.schema_id}")
    base = path.parent
    if len(project.representations) < 2:
        raise ValueError("intent project requires at least two representations")
    representation_ids = [item.id for item in project.representations]
    if len(representation_ids) != len(set(representation_ids)):
        raise ValueError("intent project representation ids must be unique")
    if len(project.preferred_authoring) != len(set(project.preferred_authoring)):
        raise ValueError("intent project preferredAuthoring entries must be unique")

    schema_document = (
        _load_object(_resolve_project_member(base, project.schema_ref, label="schemaRef"))
        if project.schema_ref
        else None
    )
    representations = []
    for item in project.representations:
        source_path = _resolve_project_member(base, item.path, label=f"representation {item.id!r} path")
        representations.append(
            {
                "id": item.id,
                "source": source_path.read_text(encoding="utf-8"),
                "sourceName": source_path.as_posix(),
                "dialect": item.dialect,
            }
        )
    report = analyze_inline_representations(
        runtime,
        InlineIntentAnalysisRequest(id=project.id, schema=schema_document, representations=representations),
    )
    report.source_project = path.as_posix()
    report.recommended_authoring = _preferred_result(report.representations, project.preferred_authoring)
    return report


def todo2code_evidence(report: IntentFormatAnalysis) -> dict[str, Any]:
    return {
        "schema": "wellm.todo2code-format-evidence/v1",
        "analysisId": report.id,
        "equivalent": report.equivalent,
        "semanticSha256": report.canonical_semantic_sha256,
        "representations": [
            {
                "id": item.id,
                "path": item.path,
                "dialect": item.detected_dialect or item.requested_dialect,
                "artifactSha256": item.artifact_sha256,
                "semanticSha256": item.semantic_sha256,
                "schemaValid": item.schema_valid,
            }
            for item in report.representations
        ],
        "pairs": [item.model_dump(mode="json") for item in report.pairs],
        "diagnostics": [item.model_dump(mode="json") for item in report.diagnostics],
        "todo2code": {
            "epistemicClass": "fact",
            "confidence": 1.0 if report.equivalent else 0.0,
            "suggestedSource": "configuration",
        },
    }

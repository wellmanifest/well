from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class SourcePosition(BaseModel):
    line: int = 1
    column: int = 1


class SourceRange(BaseModel):
    start: SourcePosition = Field(default_factory=SourcePosition)
    end: SourcePosition = Field(default_factory=SourcePosition)


class Diagnostic(BaseModel):
    code: str
    severity: Severity
    message: str
    phase: str = "runtime"
    dialect: str | None = None
    path: str | None = None
    schema_path: str | None = None
    source: str | None = None
    range: SourceRange | None = None
    hint: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class DocumentMetadata(BaseModel):
    source_dialect: str
    document_kind: Literal["data", "schema", "policy", "api", "module", "ir"] = "data"
    schema_dialect: str | None = None
    schema_ref: str | None = None
    runtime_version: str = "0.2.0rc2"
    ir_version: str = "wellmanifest-ir/v1"
    source_name: str | None = None
    directives: dict[str, Any] = Field(default_factory=dict)
    type_hints: dict[str, str] = Field(default_factory=dict)


class Document(BaseModel):
    metadata: DocumentMetadata
    data: Any = None
    ir: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    source_text: str | None = None

    @property
    def ok(self) -> bool:
        return not any(item.severity == Severity.ERROR for item in self.diagnostics)


class RuntimeTarget(BaseModel):
    runtime_ref: str = "runtime:backend-python@1"
    environment: Literal[
        "frontend", "backend", "firmware", "rpi", "iot", "digital-twin", "server", "remote"
    ] = "backend"
    execution: Literal["local", "remote", "auto"] = "auto"
    resources: dict[str, Any] = Field(default_factory=dict)


class Envelope(BaseModel):
    spec: Literal["wellmanifest.protocol/v1"] = "wellmanifest.protocol/v1"
    id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str | None = None
    causation_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    kind: Literal["command", "query", "event", "result", "diagnostic", "handshake"] = "command"
    operation: str
    content_type: str = "application/wellmanifest+json"
    accept: list[str] = Field(default_factory=lambda: ["application/wellmanifest+json"])
    schema_ref: str | None = None
    contract_ref: str | None = None
    idempotency_key: str | None = None
    runtime: RuntimeTarget = Field(default_factory=RuntimeTarget)
    payload: Any = Field(default_factory=dict)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: Any
    source_dialect: str = "auto"
    target_dialect: str = "json"
    projection: Literal["data", "ir"] = "data"
    schema_document: dict[str, Any] | None = Field(default=None, alias="schema", serialization_alias="schema")
    source_name: str | None = None
    pretty: bool = True


class ConversionResponse(BaseModel):
    output: str | dict[str, Any] | list[Any] | None
    source_dialect: str
    target_dialect: str
    projection: str
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    lossiness: Literal["LOSSLESS", "NORMALIZED", "LOSSY", "UNSUPPORTED"] = "LOSSLESS"


class ValidationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: Any
    dialect: str = "auto"
    schema_document: dict[str, Any] = Field(alias="schema", serialization_alias="schema")
    source_name: str | None = None


class ValidationResponse(BaseModel):
    valid: bool
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    normalized: Any = None


class ExecuteRequest(BaseModel):
    uri: str
    payload: Any = Field(default_factory=dict)
    mode: Literal["query", "command", "execute", "plan", "dry-run"] = "execute"
    contract_ref: str | None = None
    allowed_uri_processes: list[str] = Field(default_factory=list)
    run_id: str = ""
    runtime: RuntimeTarget = Field(default_factory=RuntimeTarget)


class ExecuteResponse(BaseModel):
    ok: bool
    run_id: str
    uri: str
    result: Any = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)

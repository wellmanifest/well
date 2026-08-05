from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from .dialects import DialectError, DialectRegistry
from .eventstore import JsonlEventStore
from .governance import available_profiles, semantic_diff, semantic_sha256, serialize_profile
from .models import (
    ConversionRequest,
    ConversionResponse,
    Diagnostic,
    Document,
    DocumentMetadata,
    Envelope,
    ExecuteRequest,
    ExecuteResponse,
    Severity,
    ValidationRequest,
    ValidationResponse,
)
from .negotiation import FormatNegotiator
from .schema import SchemaValidator
from .security import (
    AuthorizationError,
    ContractStore,
    assert_concrete_uri,
    assert_safe_run_id,
    matches_uri_process,
)
from .situation import evaluate_situation_profile
from .version import __version__

ProcessHandler = Callable[[Any, dict[str, Any]], Any]


class RuntimeExecutionError(RuntimeError):
    def __init__(self, code: str, message: str, *, status: int = 422, details: Any = None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.details = details


class WellManifestRuntime:
    version = __version__

    def __init__(
        self,
        *,
        registry: DialectRegistry | None = None,
        event_store: JsonlEventStore | None = None,
        contract_store: ContractStore | None = None,
    ):
        self.registry = registry or DialectRegistry()
        self.schema_validator = SchemaValidator()
        self.negotiator = FormatNegotiator(self.registry)
        root = Path(__file__).resolve().parents[2]
        event_path = os.getenv("WELLMANIFEST_EVENT_STORE")
        self.events = event_store or JsonlEventStore(event_path)
        contract_path = os.getenv("WELLMANIFEST_CONTRACTS")
        repository_contracts = root / "config" / "contracts.json"
        packaged_contracts = Path(__file__).resolve().parent / "resources" / "contracts.json"
        default_contract_path = repository_contracts if repository_contracts.exists() else packaged_contracts
        self.contracts = contract_store or ContractStore(contract_path or default_contract_path)
        self.processes: dict[str, ProcessHandler] = {}
        self._idempotency: dict[str, ExecuteResponse] = {}
        self._idempotency_lock = threading.Lock()
        self._register_builtin_processes()

    def parse(self, source: Any, *, dialect: str = "auto", source_name: str | None = None) -> Document:
        if not isinstance(source, str):
            metadata = DocumentMetadata(source_dialect="json@rfc8259", source_name=source_name)
            return Document(metadata=metadata, data=source, ir={"kind": "data", "value": source})
        selected = self.registry.detect(source, source_name=source_name) if dialect == "auto" else self.registry.get(dialect)
        return selected.parse(source, source_name=source_name)

    def convert(self, request: ConversionRequest | dict[str, Any]) -> ConversionResponse:
        request = request if isinstance(request, ConversionRequest) else ConversionRequest.model_validate(request)
        diagnostics: list[Diagnostic] = []
        try:
            document = self.parse(request.source, dialect=request.source_dialect, source_name=request.source_name)
            diagnostics.extend(document.diagnostics)
        except (DialectError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            code = exc.code if isinstance(exc, DialectError) else "WM-PARSE-000"
            diagnostics.append(
                Diagnostic(
                    code=code,
                    severity=Severity.ERROR,
                    phase="parse",
                    dialect=request.source_dialect,
                    source=request.source_name,
                    message=str(exc),
                )
            )
            return ConversionResponse(
                output=None,
                source_dialect=request.source_dialect,
                target_dialect=request.target_dialect,
                projection=request.projection,
                diagnostics=diagnostics,
                lossiness="UNSUPPORTED",
            )

        if request.schema_document is not None and request.projection == "data":
            diagnostics.extend(self.schema_validator.validate(
                document.data,
                request.schema_document,
                source=request.source_name,
                source_map=document.source_map,
            ))

        try:
            target = self.registry.get(request.target_dialect)
            if request.projection == "data" and document.data is None:
                raise ValueError(
                    f"Dialect {document.metadata.source_dialect} has no plain data projection; use projection=ir"
                )
            output = target.emit(document, projection=request.projection, pretty=request.pretty)
        except (ValueError, TypeError, KeyError) as exc:
            diagnostics.append(
                Diagnostic(
                    code="WM-CONVERT-001",
                    severity=Severity.ERROR,
                    phase="convert",
                    dialect=request.target_dialect,
                    source=request.source_name,
                    message=str(exc),
                )
            )
            return ConversionResponse(
                output=None,
                source_dialect=document.metadata.source_dialect,
                target_dialect=request.target_dialect,
                projection=request.projection,
                diagnostics=diagnostics,
                lossiness="UNSUPPORTED",
            )

        lossiness = self._lossiness(document.metadata.source_dialect, target.name, request.projection)
        return ConversionResponse(
            output=output,
            source_dialect=document.metadata.source_dialect,
            target_dialect=target.name,
            projection=request.projection,
            diagnostics=diagnostics,
            lossiness=lossiness,
        )

    def validate(self, request: ValidationRequest | dict[str, Any]) -> ValidationResponse:
        request = request if isinstance(request, ValidationRequest) else ValidationRequest.model_validate(request)
        try:
            document = self.parse(request.source, dialect=request.dialect, source_name=request.source_name)
        except (DialectError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            code = exc.code if isinstance(exc, DialectError) else "WM-PARSE-000"
            diagnostic = Diagnostic(
                code=code,
                severity=Severity.ERROR,
                phase="parse",
                dialect=request.dialect,
                source=request.source_name,
                message=str(exc),
            )
            return ValidationResponse(valid=False, diagnostics=[diagnostic])
        diagnostics = [*document.diagnostics]
        diagnostics.extend(self.schema_validator.validate(
                document.data,
                request.schema_document,
                source=request.source_name,
                source_map=document.source_map,
            ))
        valid = not any(item.severity == Severity.ERROR for item in diagnostics)
        return ValidationResponse(valid=valid, diagnostics=diagnostics, normalized=document.data)

    def register_process(self, uri: str, handler: ProcessHandler) -> None:
        concrete = assert_concrete_uri(uri)
        self.processes[concrete] = handler

    def execute_uri(self, request: ExecuteRequest | dict[str, Any]) -> ExecuteResponse:
        request = request if isinstance(request, ExecuteRequest) else ExecuteRequest.model_validate(request)
        try:
            uri = assert_concrete_uri(request.uri)
            run_id = assert_safe_run_id(request.run_id) or str(uuid4())
            contract_scopes = self.contracts.resolve_scopes(request.contract_ref) if request.contract_ref else []
            scopes = contract_scopes or list(request.allowed_uri_processes)
            if not scopes and os.getenv("WELLMANIFEST_DEV_ALLOW", "0") == "1":
                scopes = ["wellmanifest://*", "demo://*"]
            if not matches_uri_process(uri, scopes):
                raise AuthorizationError("WM-AUTH-006", "uri_process_not_allowed")
            handler = self.processes.get(uri)
            if handler is None:
                raise RuntimeExecutionError("WM-RUNTIME-404", f"No process handler registered for {uri}", status=404)
        except (AuthorizationError, RuntimeExecutionError) as exc:
            return ExecuteResponse(
                ok=False,
                run_id=request.run_id or "",
                uri=request.uri,
                diagnostics=[
                    Diagnostic(
                        code=exc.code,
                        severity=Severity.ERROR,
                        phase="authorize" if isinstance(exc, AuthorizationError) else "execute",
                        message=str(exc),
                        details={"status": getattr(exc, "status", 403)},
                    )
                ],
            )

        idempotency_key = request.run_id or ""
        if idempotency_key:
            with self._idempotency_lock:
                cached = self._idempotency.get(idempotency_key)
                if cached is not None:
                    return cached.model_copy(deep=True)

        requested_event = self.events.append(
            "ProcessRequested",
            {
                "uri": uri,
                "mode": request.mode,
                "runtime": request.runtime.model_dump(mode="json"),
                "contractRef": request.contract_ref,
            },
            stream=f"run:{run_id}",
            correlation_id=run_id,
        )
        context = {
            "runtime": self,
            "run_id": run_id,
            "uri": uri,
            "mode": request.mode,
            "scopes": scopes,
            "contract_ref": request.contract_ref,
            "target": request.runtime.model_dump(mode="json"),
        }
        try:
            result = handler(request.payload, context)
            completed_event = self.events.append(
                "ProcessCompleted",
                {"uri": uri, "result": result},
                stream=f"run:{run_id}",
                correlation_id=run_id,
                causation_id=requested_event["id"],
            )
            response = ExecuteResponse(
                ok=True,
                run_id=run_id,
                uri=uri,
                result={"value": result},
                events=[requested_event, completed_event],
            )
        except Exception as exc:  # Process adapters are isolated at this boundary.
            code = getattr(exc, "code", "WM-RUNTIME-500")
            status = int(getattr(exc, "status", 422))
            failed_event = self.events.append(
                "ProcessFailed",
                {"uri": uri, "code": code, "message": str(exc)},
                stream=f"run:{run_id}",
                correlation_id=run_id,
                causation_id=requested_event["id"],
            )
            response = ExecuteResponse(
                ok=False,
                run_id=run_id,
                uri=uri,
                diagnostics=[
                    Diagnostic(
                        code=code,
                        severity=Severity.ERROR,
                        phase="execute",
                        message=str(exc),
                        details={"status": status, "adapterDetails": getattr(exc, "details", None)},
                    )
                ],
                events=[requested_event, failed_event],
            )
        if idempotency_key:
            with self._idempotency_lock:
                self._idempotency[idempotency_key] = response.model_copy(deep=True)
        return response

    def exchange(self, envelope: Envelope | dict[str, Any]) -> Envelope:
        envelope = envelope if isinstance(envelope, Envelope) else Envelope.model_validate(envelope)
        payload = envelope.payload
        source_dialect = self._dialect_for_media_type(envelope.content_type)
        if isinstance(payload, str) and source_dialect:
            parsed = self.parse(payload, dialect=source_dialect)
            payload = parsed.data if parsed.data is not None else parsed.ir
        execution = self.execute_uri(
            ExecuteRequest(
                uri=envelope.operation,
                payload=payload,
                mode="query" if envelope.kind == "query" else "execute",
                contract_ref=envelope.contract_ref,
                run_id=envelope.idempotency_key or "",
                runtime=envelope.runtime,
            )
        )
        target = self.negotiator.negotiate("json", envelope.accept)
        response_payload: Any = execution.model_dump(mode="json")
        content_type = "application/wellmanifest+json"
        if target.dialect != "json@rfc8259":
            converted = self.convert(
                ConversionRequest(
                    source=response_payload,
                    source_dialect="json",
                    target_dialect=target.dialect,
                    projection="data",
                )
            )
            if converted.output is not None:
                response_payload = converted.output
                content_type = target.media_type
        return Envelope(
            kind="result" if execution.ok else "diagnostic",
            operation=envelope.operation,
            correlation_id=envelope.id,
            causation_id=envelope.id,
            content_type=content_type,
            accept=envelope.accept,
            schema_ref=envelope.schema_ref,
            contract_ref=envelope.contract_ref,
            runtime=envelope.runtime,
            payload=response_payload,
            diagnostics=execution.diagnostics,
        )

    def capabilities(self) -> dict[str, Any]:
        return {
            "protocol": "wellmanifest.protocol/v1",
            "runtimeVersion": self.version,
            "irVersion": "wellmanifest-ir/v1",
            "schemaDialects": ["json-schema@2020-12"],
            "formatProfiles": available_profiles(),
            "dialects": self.registry.describe(),
            "transports": ["http", "websocket", "mqtt-v5", "grpc"],
            "processes": sorted(self.processes),
            "runtimes": self.runtime_descriptors(),
            "diagnosticSeverities": ["ERROR", "WARNING", "INFO"],
            "projections": ["data", "ir"],
            "extensions": {
                "pleskPublication": {
                    "schema": "subactor.projects/v1",
                    "contract": "contract:plesk-publication",
                    "modes": ["plan", "dry-run", "apply", "verify"],
                    "defaultMutationMode": "dry-run",
                },
                "llmBenchmark": {
                    "schema": "wellmanifest.llm-benchmark/v1",
                    "formats": ["json", "yaml", "typed", "hcl", "typescript"],
                    "selection": ["lowest_cost", "lowest_latency", "highest_score"],
                },
            },
            "security": {
                "concreteUriRequired": True,
                "wildcardsOnlyInContracts": True,
                "remoteArbitraryCodeExecution": False,
            },
        }

    @staticmethod
    def runtime_descriptors() -> list[dict[str, Any]]:
        return [
            {
                "id": "runtime:frontend-wasm@1",
                "environment": "frontend",
                "mode": "local-or-remote",
                "artifacts": ["wellmanifest-wasm", "@wellmanifest/wellm-sdk"],
                "features": ["json", "yaml", "schema", "ws"],
            },
            {
                "id": "runtime:backend-python@1",
                "environment": "backend",
                "mode": "local-or-service",
                "artifacts": ["wellm", "wellm-server", "wellmanifest compatibility alias"],
                "features": ["all-reference-dialects", "http", "ws", "mqtt", "grpc", "cqrs-es"],
            },
            {
                "id": "runtime:backend-rust@1",
                "environment": "backend",
                "mode": "native",
                "artifacts": ["wellmanifest-core", "wellmanifest-cli"],
                "features": ["json", "yaml", "wasm", "ffi"],
            },
            {
                "id": "runtime:firmware-thin@1",
                "environment": "firmware",
                "mode": "remote",
                "artifacts": ["MicroPython HTTP/MQTT client", "C envelope header"],
                "features": ["small-envelope", "remote-convert", "remote-execute"],
            },
            {
                "id": "runtime:rpi-edge@1",
                "environment": "rpi",
                "mode": "sidecar-or-remote",
                "artifacts": ["Python client", "ARM64 container"],
                "features": ["gpio-plan", "mqtt", "offline-event-buffer"],
            },
            {
                "id": "runtime:digital-twin-readonly@1",
                "environment": "digital-twin",
                "mode": "remote",
                "artifacts": ["twin profile schema", "router query"],
                "features": ["read-only-portrait", "authority-fit", "workload-routing"],
            },
        ]

    @staticmethod
    def _lossiness(source: str, target: str, projection: str) -> str:
        if projection == "ir":
            return "LOSSLESS"
        if source == target:
            return "LOSSLESS"
        if source in {"json@rfc8259", "yaml@1.2/json-compatible", "hcl@2", "typed@1"} and target in {
            "json@rfc8259",
            "yaml@1.2/json-compatible",
            "hcl@2",
            "typed@1",
        }:
            return "NORMALIZED"
        return "LOSSY"

    def _dialect_for_media_type(self, media_type: str) -> str | None:
        try:
            return self.registry.get(media_type.split(";", 1)[0].strip()).name
        except KeyError:
            return None

    def _register_builtin_processes(self) -> None:
        self.register_process("wellmanifest://runtime/convert/execute", self._process_convert)
        self.register_process("wellmanifest://runtime/validate/execute", self._process_validate)
        self.register_process("wellmanifest://runtime/format/execute", self._process_format)
        self.register_process("wellmanifest://runtime/semantic-diff/query", self._process_semantic_diff)
        self.register_process("wellmanifest://application/run/execute", self._process_application)
        self.register_process("wellmanifest://events/stream/query", self._process_events_query)
        self.register_process("situation://profile/evaluate/query", self._process_situation)
        self.register_process("twin://router/delegation/query/decide", self._process_twin_route)
        self.register_process("twin://system/profile/query/get", self._process_twin_profile)
        self.register_process("youtube://channel/video/query/list", self._process_youtube_demo)
        self.register_process("flow://host/remote-access/query/preflight", self._process_remote_preflight)
        self.register_process("gpio://rpi/pin/configure/plan", self._process_gpio_plan)
        self.register_process("soa://service/http/request/plan", self._process_http_plan)
        self.register_process("llm://planner/manifest/query/propose", self._process_llm_plan)

    def _process_convert(self, payload: Any, _context: dict[str, Any]) -> Any:
        return self.convert(ConversionRequest.model_validate(payload)).model_dump(mode="json")

    def _process_validate(self, payload: Any, _context: dict[str, Any]) -> Any:
        return self.validate(ValidationRequest.model_validate(payload)).model_dump(mode="json")

    @staticmethod
    def _process_format(payload: Any, _context: dict[str, Any]) -> Any:
        payload = payload or {}
        value = payload.get("value")
        profile = str(payload.get("profile", "repo-json@1"))
        schema = payload.get("schema")
        output = serialize_profile(value, profile, schema=schema if isinstance(schema, dict) else None)
        return {
            "profile": profile,
            "semanticSha256": semantic_sha256(value),
            "output": output,
        }

    @staticmethod
    def _process_semantic_diff(payload: Any, _context: dict[str, Any]) -> Any:
        payload = payload or {}
        return semantic_diff(payload.get("left"), payload.get("right")).model_dump(mode="json", by_alias=True)

    def _process_events_query(self, payload: Any, _context: dict[str, Any]) -> Any:
        payload = payload or {}
        return {
            "events": self.events.read(
                stream=payload.get("stream"),
                after=int(payload.get("after", 0)),
                limit=int(payload.get("limit", 100)),
            )
        }

    def _process_situation(self, payload: Any, _context: dict[str, Any]) -> Any:
        return evaluate_situation_profile(payload["profile"], payload.get("snapshots", {}))

    @staticmethod
    def _process_twin_profile(payload: Any, context: dict[str, Any]) -> Any:
        profile = dict(payload or {})
        forbidden = {"password", "token", "secret", "credential", "privateKey"}
        sanitized = {key: value for key, value in profile.items() if key not in forbidden}
        sanitized["projection"] = "read-only"
        sanitized["authorityExpandable"] = False
        sanitized["runtimeContext"] = context.get("target")
        return sanitized

    @staticmethod
    def _process_twin_route(payload: Any, _context: dict[str, Any]) -> Any:
        requirements = set(payload.get("requirements", []))
        candidates: list[dict[str, Any]] = []
        for twin in payload.get("twins", []):
            if twin.get("contractStatus") != "active":
                continue
            authority = set(twin.get("allowedCapabilities", []))
            if not requirements.issubset(authority):
                continue
            specialties = set(twin.get("specializations", []))
            fit = len(requirements & specialties) + len(requirements)
            load = float(twin.get("workload", 0))
            candidates.append({"twin": twin, "score": fit - load})
        candidates.sort(key=lambda item: item["score"], reverse=True)
        return {"selected": candidates[0]["twin"] if candidates else None, "candidates": candidates}

    @staticmethod
    def _process_youtube_demo(payload: Any, _context: dict[str, Any]) -> Any:
        channel = (payload or {}).get("channel", "ours")
        return {
            "ok": True,
            "channel": channel,
            "items": [
                {"id": "demo-001", "title": "WellManifest protocol overview", "state": "published"},
                {"id": "demo-002", "title": "URI Process fail-closed execution", "state": "draft"},
            ],
        }

    @staticmethod
    def _process_remote_preflight(payload: Any, _context: dict[str, Any]) -> Any:
        return {
            "ok": True,
            "mutationAttempted": False,
            "checks": {
                "ticketPresent": bool((payload or {}).get("ticket_id")),
                "humanApprovalRequiredForProvision": True,
                "credentialsExposed": False,
            },
        }

    @staticmethod
    def _process_gpio_plan(payload: Any, _context: dict[str, Any]) -> Any:
        pin = int((payload or {}).get("pin", -1))
        direction = (payload or {}).get("direction")
        if pin < 0 or direction not in {"in", "out"}:
            raise RuntimeExecutionError("WM-HARDWARE-001", "Invalid GPIO plan", status=422)
        return {
            "ok": True,
            "mode": "plan",
            "steps": [
                {"action": "reserve-pin", "pin": pin},
                {"action": "configure-direction", "pin": pin, "direction": direction},
            ],
            "mutationAttempted": False,
        }

    @staticmethod
    def _process_http_plan(payload: Any, _context: dict[str, Any]) -> Any:
        method = str((payload or {}).get("method", "GET")).upper()
        url = str((payload or {}).get("url", ""))
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise RuntimeExecutionError("WM-SOA-001", "Unsupported HTTP method")
        if not url.startswith(("https://", "http://service.local/")):
            raise RuntimeExecutionError(
                "WM-SOA-002",
                "HTTP plan only accepts HTTPS or the service.local test origin; execution requires an adapter contract.",
            )
        return {"ok": True, "plan": {"method": method, "url": url, "body": (payload or {}).get("body")}, "executed": False}

    @staticmethod
    def _process_llm_plan(payload: Any, _context: dict[str, Any]) -> Any:
        goal = str((payload or {}).get("goal", "")).strip()
        if not goal:
            raise RuntimeExecutionError("WM-LLM-001", "LLM goal is required")
        return {
            "schema": "wellmanifest.llm-proposal/v1",
            "status": "PROPOSED",
            "goal": goal,
            "requiresValidation": True,
            "requiresHumanApprovalForSideEffects": True,
            "proposedManifest": {
                "runtime": {"environment": (payload or {}).get("environment", "remote")},
                "steps": [
                    {
                        "id": "analyze",
                        "uri": "wellmanifest://runtime/validate/execute",
                        "mode": "query",
                    }
                ],
            },
        }

    def _process_application(self, payload: Any, context: dict[str, Any]) -> Any:
        steps = list((payload or {}).get("steps", []))
        completed: dict[str, Any] = {}
        pending = {str(step["id"]): step for step in steps}
        while pending:
            progressed = False
            for step_id, step in list(pending.items()):
                dependencies = set(step.get("dependsOn", []))
                if not dependencies.issubset(completed):
                    continue
                if step.get("uri") == "wellmanifest://application/run/execute":
                    raise RuntimeExecutionError("WM-RUNTIME-RECURSION", "Nested application runner is forbidden")
                response = self.execute_uri(
                    ExecuteRequest(
                        uri=step["uri"],
                        payload=step.get("payload", {}),
                        mode=step.get("mode", "execute"),
                        allowed_uri_processes=context["scopes"],
                        run_id=f"{context['run_id']}:{step_id}"[:160],
                        runtime=context["target"],
                    )
                )
                if not response.ok:
                    raise RuntimeExecutionError(
                        "WM-RUNTIME-STEP",
                        f"Step {step_id} failed",
                        details=response.model_dump(mode="json"),
                    )
                completed[step_id] = response.result
                pending.pop(step_id)
                progressed = True
            if not progressed:
                raise RuntimeExecutionError("WM-RUNTIME-DAG", "Process DAG has a cycle or missing dependency")
        return {"ok": True, "steps": completed}

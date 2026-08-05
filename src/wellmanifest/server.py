from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .governance import available_profiles, semantic_diff, semantic_sha256, serialize_profile
from .models import ConversionRequest, Envelope, ExecuteRequest, ValidationRequest
from .runtime import WellManifestRuntime




class FormatApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any
    profile: str = "repo-json@1"
    schema_document: dict[str, Any] | None = Field(default=None, alias="schema", serialization_alias="schema")


class SemanticDiffApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left: Any
    right: Any


class PleskPlanApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config: dict[str, Any]
    project_id: str
    source_refs: dict[str, str] = Field(default_factory=dict)


class PleskPublishApiRequest(PleskPlanApiRequest):
    node_url: str
    contract_ref: str | None = None
    apply: bool = False
    plan_hash: str | None = None


def create_app(runtime: WellManifestRuntime | None = None) -> FastAPI:
    runtime = runtime or WellManifestRuntime()
    app = FastAPI(
        title="wellm — WellManifest Runtime Gateway",
        version=runtime.version,
        description="Polyglot dialect conversion, schema validation and capability-scoped URI Process execution.",
    )

    expected_token = os.getenv("WELLMANIFEST_TOKEN", "")
    default_contract = os.getenv("WELLMANIFEST_DEFAULT_CONTRACT", "contract:dev")

    def authorize(
        x_wellmanifest_token: Annotated[str | None, Header()] = None,
        x_urirun_token: Annotated[str | None, Header()] = None,
    ) -> None:
        supplied = x_wellmanifest_token or x_urirun_token
        if expected_token and supplied != expected_token:
            raise HTTPException(status_code=401, detail={"code": "WM-AUTH-HTTP-001", "message": "invalid token"})

    @app.get("/healthz")
    def health() -> dict[str, Any]:
        return {"status": "ok", "runtime": "wellm", "version": runtime.version}

    @app.get("/v1/capabilities", dependencies=[Depends(authorize)])
    def capabilities() -> dict[str, Any]:
        return runtime.capabilities()

    @app.get("/v1/dialects", dependencies=[Depends(authorize)])
    def dialects() -> list[dict[str, object]]:
        return runtime.registry.describe()

    @app.get("/v1/runtimes", dependencies=[Depends(authorize)])
    def runtimes() -> list[dict[str, Any]]:
        return runtime.runtime_descriptors()

    @app.get("/v1/profiles", dependencies=[Depends(authorize)])
    def profiles() -> list[dict[str, Any]]:
        return available_profiles()

    @app.post("/v1/convert", dependencies=[Depends(authorize)])
    def convert(request: ConversionRequest) -> dict[str, Any]:
        return runtime.convert(request).model_dump(mode="json")

    @app.post("/v1/validate", dependencies=[Depends(authorize)])
    def validate(request: ValidationRequest) -> dict[str, Any]:
        return runtime.validate(request).model_dump(mode="json")

    @app.post("/v1/format", dependencies=[Depends(authorize)])
    def format_document(request: FormatApiRequest) -> dict[str, Any]:
        try:
            output = serialize_profile(request.value, request.profile, schema=request.schema_document)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "WM-FORMAT-HTTP-001", "message": str(exc)},
            ) from exc
        return {
            "profile": request.profile,
            "semanticSha256": semantic_sha256(request.value),
            "output": output,
        }

    @app.post("/v1/semantic-diff", dependencies=[Depends(authorize)])
    def compare_semantics(request: SemanticDiffApiRequest) -> dict[str, Any]:
        return semantic_diff(request.left, request.right).model_dump(mode="json", by_alias=True)

    @app.post("/v1/negotiate", dependencies=[Depends(authorize)])
    def negotiate(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            selected = runtime.negotiator.negotiate(payload.get("sourceDialect", "json"), payload.get("accept", []))
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=406, detail={"code": "WM-NEGOTIATE-001", "message": str(exc)}) from exc
        return {
            "mediaType": selected.media_type,
            "dialect": selected.dialect,
            "conversionRequired": selected.conversion_required,
        }

    @app.post("/v1/runtime/execute", dependencies=[Depends(authorize)])
    def execute(request: ExecuteRequest) -> dict[str, Any]:
        if not request.contract_ref and not request.allowed_uri_processes:
            request = request.model_copy(update={"contract_ref": default_contract})
        response = runtime.execute_uri(request)
        return response.model_dump(mode="json")

    @app.post("/run", dependencies=[Depends(authorize)])
    def urirun_compat(
        payload: dict[str, Any],
        x_urirun_run_id: Annotated[str | None, Header()] = None,
        x_wellmanifest_contract: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        request = ExecuteRequest(
            uri=payload.get("uri", ""),
            payload=payload.get("payload", {}),
            mode=payload.get("mode", "execute"),
            run_id=x_urirun_run_id or payload.get("runId", ""),
            contract_ref=x_wellmanifest_contract or payload.get("contractRef") or default_contract,
            allowed_uri_processes=payload.get("allowedUriProcesses", []),
            runtime=payload.get("runtime", {}),
        )
        response = runtime.execute_uri(request)
        if not response.ok:
            status = 422
            if response.diagnostics:
                status = int(response.diagnostics[0].details.get("status", status))
            raise HTTPException(status_code=status, detail=response.model_dump(mode="json"))
        return response.model_dump(mode="json")

    @app.post("/v1/plesk/plan", dependencies=[Depends(authorize)])
    def plesk_plan(request: PleskPlanApiRequest) -> dict[str, Any]:
        from .plesk import PleskPublicationPlanner, ProjectRegistry, WorkspaceResolver

        workspace_root_raw = os.getenv("WELLMANIFEST_WORKSPACE_ROOT", "")
        if not workspace_root_raw:
            raise HTTPException(
                status_code=503,
                detail={"code": "WM-PLESK-HTTP-001", "message": "WELLMANIFEST_WORKSPACE_ROOT is not configured"},
            )
        workspace_root = Path(workspace_root_raw).resolve()
        mappings = {
            key: (Path(value) if Path(value).is_absolute() else workspace_root / value)
            for key, value in request.source_refs.items()
        }
        try:
            registry = ProjectRegistry.model_validate(request.config)
            plan = PleskPublicationPlanner(
                registry,
                WorkspaceResolver(mappings=mappings, workspace_root=workspace_root),
            ).build(request.project_id)
        except (ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "WM-PLESK-HTTP-002", "message": str(exc)},
            ) from exc
        return plan.model_dump(mode="json", by_alias=True)

    @app.post("/v1/plesk/publish", dependencies=[Depends(authorize)])
    def plesk_publish(
        request: PleskPublishApiRequest,
        x_urirun_token: Annotated[str | None, Header()] = None,
        x_urirun_apply_grant: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        if os.getenv("WELLMANIFEST_ENABLE_PLESK_EXECUTION", "0") != "1":
            raise HTTPException(
                status_code=403,
                detail={"code": "WM-PLESK-HTTP-003", "message": "Remote Plesk execution is disabled"},
            )
        from .plesk import PleskPublicationExecutor, PleskPublicationPlanner, ProjectRegistry, WorkspaceResolver
        from .urirun import UrirunProcessClient

        workspace_root_raw = os.getenv("WELLMANIFEST_WORKSPACE_ROOT", "")
        if not workspace_root_raw:
            raise HTTPException(
                status_code=503,
                detail={"code": "WM-PLESK-HTTP-001", "message": "WELLMANIFEST_WORKSPACE_ROOT is not configured"},
            )
        workspace_root = Path(workspace_root_raw).resolve()
        mappings = {
            key: (Path(value) if Path(value).is_absolute() else workspace_root / value)
            for key, value in request.source_refs.items()
        }
        try:
            registry = ProjectRegistry.model_validate(request.config)
            plan = PleskPublicationPlanner(
                registry,
                WorkspaceResolver(mappings=mappings, workspace_root=workspace_root),
            ).build(request.project_id)
            client = UrirunProcessClient(
                node_url=request.node_url,
                token=x_urirun_token or "",
                contract_ref=request.contract_ref or registry.connector.contract_ref,
            )
            executor = PleskPublicationExecutor(client)
            dry = executor.dry_run(plan)
            receipt = dry
            if request.apply:
                receipt = executor.apply(
                    plan,
                    plan_hash=request.plan_hash or "",
                    apply_grant=x_urirun_apply_grant or "",
                    dry_run_receipt=dry,
                )
        except (ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "WM-PLESK-HTTP-004", "message": str(exc)},
            ) from exc
        return receipt.model_dump(mode="json", by_alias=True)

    @app.post("/v1/envelopes", dependencies=[Depends(authorize)])
    def exchange(envelope: Envelope) -> dict[str, Any]:
        return runtime.exchange(envelope).model_dump(mode="json")

    @app.get("/v1/events", dependencies=[Depends(authorize)])
    def events(stream: str | None = None, after: int = 0, limit: int = 100) -> dict[str, Any]:
        return {"events": runtime.events.read(stream=stream, after=after, limit=limit)}

    @app.websocket("/v1/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        token = websocket.query_params.get("token", "")
        if expected_token and token != expected_token:
            await websocket.close(code=4401, reason="invalid token")
            return
        await websocket.accept(subprotocol="wellmanifest.v1")
        await websocket.send_json({"kind": "handshake", "capabilities": runtime.capabilities()})
        try:
            while True:
                message = await websocket.receive_json()
                operation = message.get("op")
                request_id = message.get("id")
                if operation == "convert":
                    result = runtime.convert(message.get("request", {})).model_dump(mode="json")
                elif operation == "validate":
                    result = runtime.validate(message.get("request", {})).model_dump(mode="json")
                elif operation == "format":
                    request = FormatApiRequest.model_validate(message.get("request", {}))
                    result = {
                        "profile": request.profile,
                        "semanticSha256": semantic_sha256(request.value),
                        "output": serialize_profile(request.value, request.profile, schema=request.schema_document),
                    }
                elif operation == "semantic-diff":
                    request = SemanticDiffApiRequest.model_validate(message.get("request", {}))
                    result = semantic_diff(request.left, request.right).model_dump(mode="json", by_alias=True)
                elif operation == "execute":
                    request = ExecuteRequest.model_validate(message.get("request", {}))
                    if not request.contract_ref and not request.allowed_uri_processes:
                        request = request.model_copy(update={"contract_ref": default_contract})
                    result = runtime.execute_uri(request).model_dump(mode="json")
                elif operation == "exchange":
                    result = runtime.exchange(message.get("envelope", {})).model_dump(mode="json")
                else:
                    result = {
                        "ok": False,
                        "diagnostics": [
                            {
                                "code": "WM-WS-001",
                                "severity": "ERROR",
                                "message": f"Unknown WebSocket operation: {operation}",
                            }
                        ],
                    }
                await websocket.send_json({"id": request_id, "op": operation, "result": result})
        except WebSocketDisconnect:
            return
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            await websocket.send_json(
                {
                    "kind": "diagnostic",
                    "diagnostics": [{"code": "WM-WS-500", "severity": "ERROR", "message": str(exc)}],
                }
            )
            await websocket.close(code=1011)

    root = Path(__file__).resolve().parents[2]
    repository_www = root / "www"
    packaged_www = Path(__file__).resolve().parent / "static"
    www = repository_www if repository_www.exists() else packaged_www
    if (www / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=www), name="assets")

        @app.get("/")
        def landing() -> FileResponse:
            return FileResponse(www / "index.html")

    return app


app = create_app()


def main() -> None:
    uvicorn.run(
        "wellmanifest.server:app",
        host=os.getenv("WELLMANIFEST_HOST", "0.0.0.0"),
        port=int(os.getenv("WELLMANIFEST_PORT", "8080")),
        reload=os.getenv("WELLMANIFEST_RELOAD", "0") == "1",
    )


if __name__ == "__main__":
    main()

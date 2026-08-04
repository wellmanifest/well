from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import ConversionRequest, Envelope, ExecuteRequest, ValidationRequest
from .runtime import WellManifestRuntime


def create_app(runtime: WellManifestRuntime | None = None) -> FastAPI:
    runtime = runtime or WellManifestRuntime()
    app = FastAPI(
        title="WellManifest Runtime Gateway",
        version=runtime.version,
        description="Polyglot dialect conversion, schema validation and capability-scoped URI Process execution.",
    )

    expected_token = os.getenv("WELLMANIFEST_TOKEN", "")
    default_contract = os.getenv("WELLMANIFEST_DEFAULT_CONTRACT", "contract:dev")

    def authorize(x_wellmanifest_token: Annotated[str | None, Header()] = None) -> None:
        if expected_token and x_wellmanifest_token != expected_token:
            raise HTTPException(status_code=401, detail={"code": "WM-AUTH-HTTP-001", "message": "invalid token"})

    @app.get("/healthz")
    def health() -> dict[str, Any]:
        return {"status": "ok", "runtime": "wellmanifest", "version": runtime.version}

    @app.get("/v1/capabilities", dependencies=[Depends(authorize)])
    def capabilities() -> dict[str, Any]:
        return runtime.capabilities()

    @app.get("/v1/dialects", dependencies=[Depends(authorize)])
    def dialects() -> list[dict[str, object]]:
        return runtime.registry.describe()

    @app.get("/v1/runtimes", dependencies=[Depends(authorize)])
    def runtimes() -> list[dict[str, Any]]:
        return runtime.runtime_descriptors()

    @app.post("/v1/convert", dependencies=[Depends(authorize)])
    def convert(request: ConversionRequest) -> dict[str, Any]:
        return runtime.convert(request).model_dump(mode="json")

    @app.post("/v1/validate", dependencies=[Depends(authorize)])
    def validate(request: ValidationRequest) -> dict[str, Any]:
        return runtime.validate(request).model_dump(mode="json")

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

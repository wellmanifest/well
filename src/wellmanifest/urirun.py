from __future__ import annotations

from typing import Any

import httpx

from .security import assert_concrete_uri, assert_safe_run_id, matches_uri_process


class UrirunError(RuntimeError):
    """Error returned by a remote urirun node or rejected by the local guard."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "urirun_error",
        status: int = 422,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.details = details


class UrirunProcessClient:
    """Minimal client for the canonical ``POST {node_url}/run`` boundary.

    ``allowed_uri_processes`` is an early client-side rejection only.  The
    server-side Contract AQL remains the authority boundary.
    """

    def __init__(
        self,
        *,
        node_url: str,
        token: str = "",
        contract_ref: str = "contract:dev",
        timeout: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.node_url = str(node_url or "").rstrip("/")
        self.token = str(token or "")
        self.contract_ref = str(contract_ref or "")
        self.timeout = float(timeout)
        self._client = client

    def execute(
        self,
        uri: str,
        payload: Any | None = None,
        *,
        mode: str = "execute",
        allowed_uri_processes: list[str] | tuple[str, ...] = (),
        run_id: str = "",
    ) -> dict[str, Any]:
        if not self.node_url:
            raise UrirunError("urirun_node_not_configured", code="urirun_node_not_configured", status=400)

        try:
            concrete_uri = assert_concrete_uri(uri)
            correlated_run_id = assert_safe_run_id(run_id)
        except Exception as exc:
            code = getattr(exc, "code", "uri_process_uri_invalid")
            raise UrirunError(str(exc), code=code, status=400) from exc

        scopes = [str(item) for item in allowed_uri_processes]
        if scopes and not matches_uri_process(concrete_uri, scopes):
            raise UrirunError("uri_process_not_allowed", code="uri_process_not_allowed", status=403)

        headers = {"content-type": "application/json", "accept": "application/json"}
        if self.token:
            # Canonical urirun header plus compatibility with the WellManifest gateway.
            headers["x-urirun-token"] = self.token
            headers["x-wellmanifest-token"] = self.token
        if self.contract_ref:
            headers["x-wellmanifest-contract"] = self.contract_ref
        if correlated_run_id:
            headers["x-urirun-run-id"] = correlated_run_id

        body = {"uri": concrete_uri, "mode": mode, "payload": payload or {}}
        try:
            if self._client is not None:
                response = self._client.post(f"{self.node_url}/run", headers=headers, json=body)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(f"{self.node_url}/run", headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise UrirunError(
                "urirun_node_unreachable",
                code="urirun_node_unreachable",
                status=502,
                details={"error": str(exc)},
            ) from exc

        try:
            data: Any = response.json()
        except ValueError:
            data = {"raw": response.text}

        if not response.is_success:
            raise UrirunError(
                f"urirun_node_{response.status_code}",
                code=f"urirun_node_{response.status_code}",
                status=response.status_code,
                details=data,
            )

        handler_value = data.get("result", {}).get("value") if isinstance(data, dict) else None
        if isinstance(handler_value, dict) and handler_value.get("ok") is False:
            reason = str(handler_value.get("error") or handler_value.get("reason") or "urirun_handler_failed")
            raw_status = handler_value.get("status")
            status = int(raw_status) if isinstance(raw_status, (int, float, str)) and str(raw_status).isdigit() else 422
            if not 400 <= status <= 599:
                status = 422
            raise UrirunError(
                reason,
                code="urirun_handler_failed",
                status=status,
                details=handler_value,
            )
        if not isinstance(data, dict):
            raise UrirunError(
                "urirun_response_invalid",
                code="urirun_response_invalid",
                status=502,
                details=data,
            )
        return data

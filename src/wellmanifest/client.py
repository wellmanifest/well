from __future__ import annotations

from typing import Any

import httpx


class WellManifestClient:
    def __init__(self, base_url: str, *, token: str = "", timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        return {"x-wellmanifest-token": self.token} if self.token else {}

    def capabilities(self) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/v1/capabilities", headers=self.headers)
            response.raise_for_status()
            return response.json()

    def convert(
        self,
        source: Any,
        *,
        source_dialect: str = "auto",
        target_dialect: str = "json",
        projection: str = "data",
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "source": source,
            "source_dialect": source_dialect,
            "target_dialect": target_dialect,
            "projection": projection,
            "schema": schema,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/v1/convert", json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def execute(
        self,
        uri: str,
        payload: Any | None = None,
        *,
        contract_ref: str = "contract:dev",
        run_id: str = "",
        environment: str = "remote",
    ) -> dict[str, Any]:
        request = {
            "uri": uri,
            "payload": payload or {},
            "contract_ref": contract_ref,
            "run_id": run_id,
            "runtime": {"runtime_ref": "runtime:remote-service@1", "environment": environment, "execution": "remote"},
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/v1/runtime/execute", json=request, headers=self.headers)
            response.raise_for_status()
            return response.json()


class AsyncWellManifestClient:
    def __init__(self, base_url: str, *, token: str = "", timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        return {"x-wellmanifest-token": self.token} if self.token else {}

    async def convert(self, source: Any, **options: Any) -> dict[str, Any]:
        payload = {
            "source": source,
            "source_dialect": options.get("source_dialect", "auto"),
            "target_dialect": options.get("target_dialect", "json"),
            "projection": options.get("projection", "data"),
            "schema": options.get("schema"),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/v1/convert", json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def execute(self, uri: str, payload: Any | None = None, **options: Any) -> dict[str, Any]:
        request = {
            "uri": uri,
            "payload": payload or {},
            "contract_ref": options.get("contract_ref", "contract:dev"),
            "run_id": options.get("run_id", ""),
            "runtime": {
                "runtime_ref": options.get("runtime_ref", "runtime:remote-service@1"),
                "environment": options.get("environment", "remote"),
                "execution": "remote",
            },
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/v1/runtime/execute", json=request, headers=self.headers)
            response.raise_for_status()
            return response.json()

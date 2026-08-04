from __future__ import annotations

import httpx
import pytest

from wellmanifest.server import create_app


@pytest.mark.asyncio
async def test_http_convert_validate_and_execute_e2e() -> None:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/healthz")
        assert health.json()["status"] == "ok"

        converted = await client.post(
            "/v1/convert",
            json={
                "source": "status:\n  value: SUCCEEDED\n",
                "source_dialect": "yaml",
                "target_dialect": "json",
                "projection": "data",
            },
        )
        assert converted.status_code == 200
        assert '"SUCCEEDED"' in converted.json()["output"]

        executed = await client.post(
            "/v1/runtime/execute",
            json={
                "uri": "youtube://channel/video/query/list",
                "payload": {"channel": "ours"},
                "contract_ref": "contract:dev",
                "run_id": "e2e:youtube:1",
                "runtime": {
                    "runtime_ref": "backend-python",
                    "environment": "backend",
                    "execution": "remote",
                    "resources": {},
                },
            },
        )
        assert executed.status_code == 200
        assert executed.json()["ok"] is True

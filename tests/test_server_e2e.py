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


@pytest.mark.asyncio
async def test_http_versions_env_and_intent_analysis_endpoints() -> None:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        versions = await client.get("/v1/versions")
        assert versions.status_code == 200
        assert versions.json()["package"]["version"] == "0.2.0rc4"

        env_contract = await client.get("/v1/env-contract")
        assert env_contract.status_code == 200
        assert env_contract.json()["schema"] == "wellm.env-contract/v1"
        assert all("value" not in item for item in env_contract.json()["variables"])

        analyzed = await client.post(
            "/v1/intent/analyze",
            json={
                "id": "http-intent",
                "representations": [
                    {"id": "json", "dialect": "json", "sourceName": "a.json", "source": '{"a":1}'},
                    {"id": "yaml", "dialect": "yaml", "sourceName": "a.yaml", "source": "a: 1\n"},
                ],
            },
        )
        assert analyzed.status_code == 200
        assert analyzed.json()["equivalent"] is True

from __future__ import annotations

from fastapi.testclient import TestClient

from wellmanifest.server import create_app


def test_http_format_and_semantic_diff_endpoints() -> None:
    client = TestClient(create_app())
    response = client.post("/v1/format", json={"value": {"b": 2, "a": 1}, "profile": "wire-json@1"})
    assert response.status_code == 200
    body = response.json()
    assert body["output"] == '{"a":1,"b":2}\n'
    assert body["semanticSha256"].startswith("sha256:")

    response = client.post("/v1/semantic-diff", json={"left": {"a": 1}, "right": {"a": 2}})
    assert response.status_code == 200
    body = response.json()
    assert body["equivalent"] is False
    assert body["changes"][0]["path"] == "/a"


def test_profiles_are_exposed_as_runtime_capabilities() -> None:
    client = TestClient(create_app())
    profiles = client.get("/v1/profiles").json()
    ids = {item["id"] for item in profiles}
    assert {"repo-json@1", "wire-json@1", "yaml-json@1", "typescript-data@1"}.issubset(ids)

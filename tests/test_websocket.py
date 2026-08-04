from __future__ import annotations

from fastapi.testclient import TestClient

from wellmanifest.server import create_app


def test_websocket_conversion_and_capability_handshake() -> None:
    with TestClient(create_app()) as client:
        with client.websocket_connect("/v1/ws", subprotocols=["wellmanifest.v1"]) as socket:
            handshake = socket.receive_json()
            assert handshake["kind"] == "handshake"
            assert handshake["capabilities"]["protocol"] == "wellmanifest.protocol/v1"
            socket.send_json(
                {
                    "id": "ws-test-1",
                    "op": "convert",
                    "request": {
                        "source": "status:\n  value: SUCCEEDED\n",
                        "source_dialect": "yaml",
                        "target_dialect": "json",
                    },
                }
            )
            response = socket.receive_json()
            assert response["id"] == "ws-test-1"
            assert "SUCCEEDED" in response["result"]["output"]

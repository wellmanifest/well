from __future__ import annotations

from wellmanifest.models import Envelope, ExecuteRequest
from wellmanifest.runtime import WellManifestRuntime


def test_uri_process_executes_under_contract_and_records_events() -> None:
    runtime = WellManifestRuntime()
    response = runtime.execute_uri(
        ExecuteRequest(
            uri="youtube://channel/video/query/list",
            payload={"channel": "ours"},
            contract_ref="contract:dev",
            run_id="test:youtube:1",
        )
    )
    assert response.ok
    assert response.result["value"]["items"]
    assert [event["type"] for event in response.events] == ["ProcessRequested", "ProcessCompleted"]


def test_idempotency_reuses_completed_response() -> None:
    runtime = WellManifestRuntime()
    request = ExecuteRequest(
        uri="youtube://channel/video/query/list",
        payload={"channel": "ours"},
        contract_ref="contract:dev",
        run_id="test:idempotent:1",
    )
    first = runtime.execute_uri(request)
    count = runtime.events.count()
    second = runtime.execute_uri(request)
    assert second == first
    assert runtime.events.count() == count


def test_uri_process_fails_closed_without_scope() -> None:
    runtime = WellManifestRuntime()
    response = runtime.execute_uri(
        ExecuteRequest(uri="youtube://channel/video/query/list", payload={}, contract_ref=None)
    )
    assert not response.ok
    assert response.diagnostics[0].code == "WM-AUTH-006"


def test_application_runtime_executes_dependency_dag() -> None:
    runtime = WellManifestRuntime()
    response = runtime.execute_uri(
        {
            "uri": "wellmanifest://application/run/execute",
            "contract_ref": "contract:dev",
            "run_id": "test:dag:1",
            "payload": {
                "steps": [
                    {
                        "id": "first",
                        "uri": "youtube://channel/video/query/list",
                        "payload": {"channel": "ours"},
                    },
                    {
                        "id": "second",
                        "uri": "flow://host/remote-access/query/preflight",
                        "dependsOn": ["first"],
                        "payload": {"ticket_id": "PLF-075"},
                    },
                ]
            },
        }
    )
    assert response.ok
    assert set(response.result["value"]["steps"]) == {"first", "second"}


def test_envelope_negotiates_yaml_response() -> None:
    runtime = WellManifestRuntime()
    response = runtime.exchange(
        Envelope(
            kind="query",
            operation="youtube://channel/video/query/list",
            contract_ref="contract:dev",
            accept=["application/wellmanifest+yaml"],
            payload={"channel": "ours"},
        )
    )
    assert response.kind == "result"
    assert response.content_type == "application/wellmanifest+yaml"
    assert isinstance(response.payload, str)

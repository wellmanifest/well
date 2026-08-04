from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from wellmanifest.plesk import (
    PleskConfigurationError,
    PleskPublicationExecutor,
    PleskPublicationPlanner,
    ProjectRegistry,
    WorkspaceResolver,
)
from wellmanifest.server import create_app
from wellmanifest.urirun import UrirunError, UrirunProcessClient


@pytest.fixture
def project_data() -> dict[str, Any]:
    return {
        "schema": "subactor.projects/v1",
        "projects": [
            {
                "id": "obslugabiurowa-pl",
                "company": "ObsługaBiurowa.pl",
                "domain": "obslugabiurowa.pl",
                "subscription": "prototypowanie.pl",
                "dns_zone": "obslugabiurowa.pl",
                "dns_provider": "cloudflare",
                "dns_management_plane": "plesk",
                "dns_sync_extension": "cloudflaredns",
                "public_ingress_mode": "plesk_public_origin",
                "tunnel_mode": "none",
                "origin_ip": "217.160.250.222",
                "source": "site",
                "entrypoint": "index.html",
                "publication": {
                    "mode": "static_httpdocs",
                    "publish_uri": "plesk://host/site/command/sync",
                    "verify_uri": "plesk://host/site/command/publish-verify",
                    "source_ref": "workspace:obslugabiurowa-pl",
                    "deployment_ref": "deployment:obslugabiurowa-pl:production",
                    "verification": {"mode": "content_hash", "path": "/"},
                },
                "gates": ["subscription_can_create_domain", "dns_ready", "tls_ready"],
            }
        ],
    }


@pytest.fixture
def source_dir(tmp_path: Path) -> Path:
    path = tmp_path / "obslugabiurowa-pl" / "www"
    path.mkdir(parents=True)
    (path / "index.html").write_text("hello", encoding="utf-8")
    return path


def build_plan(project_data: dict[str, Any], source_dir: Path):
    registry = ProjectRegistry.model_validate(project_data)
    return PleskPublicationPlanner(
        registry,
        WorkspaceResolver(
            mappings={"workspace:obslugabiurowa-pl": source_dir},
            workspace_root=source_dir.parents[1],
        ),
    ).build("obslugabiurowa-pl")


def test_project_registry_and_plan_are_fail_closed(project_data: dict[str, Any], source_dir: Path) -> None:
    plan = build_plan(project_data, source_dir)
    assert len(plan.manifest_hash) == 64
    assert len(plan.steps) == 10
    assert "plesk://host/subscription/query/snapshot" in plan.allowed_uri_processes
    assert "plesk://host/site/query/docroot" in plan.allowed_uri_processes
    assert plan.twin.package == "@uri-twin/plesk"
    assert plan.twin.mode == "read-only"
    assert any(item.code == "WM-TWIN-101" for item in plan.diagnostics)
    assert all("*" not in uri for uri in plan.allowed_uri_processes)
    dry = next(step for step in plan.steps if step.id == "publish-dry-run")
    apply = next(step for step in plan.steps if step.id == "publish-apply")
    assert dry.payload["source_dir"] == str(source_dir.resolve())
    assert dry.payload["apply"] is False
    assert dry.payload["transport"] == "sftp"
    assert apply.mutation is True
    assert apply.human_approval is True


def test_source_directory_name_is_allowlisted(project_data: dict[str, Any], tmp_path: Path) -> None:
    bad = tmp_path / "private"
    bad.mkdir()
    registry = ProjectRegistry.model_validate(project_data)
    planner = PleskPublicationPlanner(
        registry,
        WorkspaceResolver(mappings={"workspace:obslugabiurowa-pl": bad}, workspace_root=tmp_path),
    )
    with pytest.raises(PleskConfigurationError, match="named www"):
        planner.build("obslugabiurowa-pl")


class FakeUrirunClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def execute(self, uri: str, payload: Any, **options: Any) -> dict[str, Any]:
        self.calls.append({"uri": uri, "payload": payload, **options})
        values = {
            "plesk://host/doctor/query/report": {"ok": True, "status": "ready"},
            "plesk://host/subscription/query/snapshot": {
                "ok": True,
                "schema": "subactor.twin-fact/v1",
                "resource": {"subscription": "prototypowanie.pl"},
            },
            "plesk://host/site/query/docroot": {
                "ok": True,
                "schema": "subactor.twin-fact/v1",
                "resource": {"domain": "obslugabiurowa.pl", "www_root": "/httpdocs"},
            },
            "plesk://host/subscription/query/capabilities": {
                "ok": True,
                "authenticated": True,
                "can_create_domain": True,
            },
            "plesk://host/dns/query/authority": {
                "ok": True,
                "provider": "cloudflare",
                "authority": {"consistent": True},
            },
            "plesk://host/dns/query/propagation": {"ok": True, "propagated": True, "consensus": True},
            "plesk://host/site/command/ssl-ensure": {
                "ok": True,
                "dry_run": True,
                "strategy": "probe",
                "probe": {"valid": True},
            },
            "plesk://host/site/command/sync": (
                {"ok": True, "executed": True, "mutation_attempted": True, "plan_hash": "connector-plan"}
                if payload.get("apply")
                else {"ok": True, "dry_run": True, "executed": False, "mutation_attempted": False, "plan_hash": "connector-plan"}
            ),
            "plesk://host/site/command/publish-verify": {"ok": True, "verified": True},
        }
        return {"ok": True, "result": {"value": values[uri]}}


def test_executor_requires_exact_dry_run_hash_and_signed_grant(project_data: dict[str, Any], source_dir: Path) -> None:
    plan = build_plan(project_data, source_dir)
    client = FakeUrirunClient()
    executor = PleskPublicationExecutor(client)  # type: ignore[arg-type]
    dry = executor.dry_run(plan)
    assert dry.ok is True
    assert dry.connector_plan_hash == "connector-plan"
    with pytest.raises(PleskConfigurationError, match="does not match"):
        executor.apply(plan, plan_hash="wrong", apply_grant="signed", dry_run_receipt=dry)
    applied = executor.apply(plan, plan_hash="connector-plan", apply_grant="signed", dry_run_receipt=dry)
    assert applied.ok is True
    apply_call = next(call for call in client.calls if call["payload"].get("apply") is True)
    assert apply_call["payload"]["plan_hash"] == "connector-plan"
    assert apply_call["payload"]["apply_grant"] == "signed"


def test_project_schema_validates_exact_user_configuration(project_data: dict[str, Any]) -> None:
    schema = json.loads(Path("schemas/projects.schema.json").read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator

    errors = list(Draft202012Validator(schema).iter_errors(project_data))
    assert errors == []


def test_http_plan_endpoint_resolves_only_under_server_workspace(
    project_data: dict[str, Any], source_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WELLMANIFEST_WORKSPACE_ROOT", str(source_dir.parents[1]))
    client = TestClient(create_app())
    response = client.post(
        "/v1/plesk/plan",
        json={
            "config": project_data,
            "project_id": "obslugabiurowa-pl",
            "source_refs": {"workspace:obslugabiurowa-pl": "obslugabiurowa-pl/www"},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["project_id"] == "obslugabiurowa-pl"


def test_urirun_network_error_becomes_structured_error() -> None:
    def failing(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    client = UrirunProcessClient(
        node_url="http://urirun.invalid",
        client=httpx.Client(transport=httpx.MockTransport(failing)),
    )
    with pytest.raises(UrirunError) as captured:
        client.execute(
            "plesk://host/doctor/query/report",
            {},
            allowed_uri_processes=["plesk://host/doctor/query/report"],
        )
    assert captured.value.code == "urirun_node_unreachable"
    assert captured.value.status == 502


def test_project_registry_roundtrips_through_exchange_formats(project_data: dict[str, Any]) -> None:
    from wellmanifest.models import ConversionRequest
    from wellmanifest.runtime import WellManifestRuntime

    runtime = WellManifestRuntime()
    for target in ("json", "yaml", "typed", "hcl", "typescript"):
        converted = runtime.convert(
            ConversionRequest(
                source=project_data,
                source_dialect="json",
                target_dialect=target,
                projection="data",
            )
        )
        assert converted.output is not None, target
        parsed = runtime.parse(str(converted.output), dialect=target)
        assert parsed.data == project_data, target

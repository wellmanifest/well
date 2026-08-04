from __future__ import annotations

import hashlib
import ipaddress
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import Diagnostic, Severity
from .security import assert_concrete_uri
from .urirun import UrirunError, UrirunProcessClient


class PleskConfigurationError(ValueError):
    pass


class VerificationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["content_hash", "http_status", "content_marker"] = "content_hash"
    path: str = "/"
    content_sha256: str | None = None
    expected_http_status: int = 200
    marker: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if not value.startswith("/") or "\n" in value or "\r" in value:
            raise ValueError("verification.path must be an absolute HTTP path")
        return value

    @field_validator("content_sha256")
    @classmethod
    def validate_sha(cls, value: str | None) -> str | None:
        if value is not None and (len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower())):
            raise ValueError("content_sha256 must be a 64-character SHA-256 hex digest")
        return value.lower() if value else value


class PublicationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["static_httpdocs", "release"] = "static_httpdocs"
    publish_uri: str = "plesk://host/site/command/sync"
    verify_uri: str = "plesk://host/site/command/publish-verify"
    source_ref: str
    deployment_ref: str
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    remote_path: str = "/httpdocs"
    transport: Literal["auto", "sftp", "ftp"] = "sftp"
    sftp_host: str | None = None
    sftp_port: int = 22
    sftp_vault_entry_id: str = "plesk-sftp"
    credential_origin: str | None = None
    host_fingerprint: str | None = None
    base_url: str | None = None
    subscription_vault_entry_id: str | None = None
    runtime_vault_entry_id: str | None = None
    vault_url: str | None = None
    actor: str | None = None
    pack_id: str | None = None
    pack_version: str | None = None

    @model_validator(mode="after")
    def validate_publication(self) -> "PublicationConfig":
        assert_concrete_uri(self.publish_uri)
        assert_concrete_uri(self.verify_uri)
        if self.mode == "static_httpdocs" and self.publish_uri not in {
            "plesk://host/site/command/sync",
            "plesk://host/site/command/publish",
        }:
            raise ValueError("static_httpdocs requires the Plesk sync/publish URI")
        if self.transport == "ftp":
            # The connector can be configured to permit FTP fallback, but WellManifest
            # should not silently select it for a production publication.
            raise ValueError("transport=ftp is not accepted by the safe publication profile; use sftp or auto")
        if not self.remote_path.startswith("/"):
            raise ValueError("remote_path must start with /")
        if self.credential_origin and not self.credential_origin.startswith("https://"):
            raise ValueError("credential_origin must use https://; credentials are never embedded in the manifest")
        return self


class ConnectorBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package: str = "urirun-connector-plesk"
    repository: str = "https://github.com/urirun-connectors/urirun-connector-plesk"
    contract_ref: str = "contract:plesk-publication"
    node_url: str | None = None


class TwinBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package: str = "@uri-twin/plesk"
    repository: str = "https://github.com/uri-twin/uri-twin-plesk"
    mode: Literal["read-only"] = "read-only"
    revision: str | None = None
    attestation_required: bool = True


class ProjectSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    company: str
    domain: str
    subscription: str
    dns_zone: str
    dns_provider: str
    dns_management_plane: str
    dns_sync_extension: str | None = None
    public_ingress_mode: str
    tunnel_mode: str
    origin_ip: str
    source: str = "site"
    entrypoint: str = "index.html"
    publication: PublicationConfig
    gates: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-._")
        if not value or any(char not in allowed for char in value):
            raise ValueError("project id must contain only lowercase letters, digits, -, . or _")
        return value

    @field_validator("domain", "subscription", "dns_zone")
    @classmethod
    def validate_dns_name(cls, value: str) -> str:
        normalized = value.strip().lower().rstrip(".")
        if not normalized or " " in normalized or "/" in normalized or "*" in normalized:
            raise ValueError("domain-like fields must contain a concrete DNS name")
        return normalized

    @field_validator("origin_ip")
    @classmethod
    def validate_ip(cls, value: str) -> str:
        return str(ipaddress.ip_address(value))

    @model_validator(mode="after")
    def validate_entrypoint(self) -> "ProjectSpec":
        if Path(self.entrypoint).is_absolute() or ".." in Path(self.entrypoint).parts:
            raise ValueError("entrypoint must be a safe relative path")
        return self


class ProjectRegistry(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    schema_id: Literal["subactor.projects/v1"] = Field(alias="schema", serialization_alias="schema")
    projects: list[ProjectSpec]
    connector: ConnectorBinding = Field(default_factory=ConnectorBinding)
    twin: TwinBinding = Field(default_factory=TwinBinding)

    @model_validator(mode="after")
    def unique_projects(self) -> "ProjectRegistry":
        ids = [project.id for project in self.projects]
        if len(ids) != len(set(ids)):
            raise ValueError("project ids must be unique")
        return self

    def get(self, project_id: str) -> ProjectSpec:
        for project in self.projects:
            if project.id == project_id:
                return project
        raise KeyError(f"Unknown project: {project_id}")


class PublicationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    uri: str
    mode: Literal["query", "dry-run", "command"]
    phase: Literal["preflight", "plan", "apply", "verify"]
    payload: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    gate: str | None = None
    mutation: bool = False
    human_approval: bool = False

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, value: str) -> str:
        return assert_concrete_uri(value)


class PublicationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["wellmanifest.plesk-publication-plan/v1"] = Field(
        default="wellmanifest.plesk-publication-plan/v1",
        alias="schema",
        serialization_alias="schema",
    )
    id: str
    project_id: str
    deployment_ref: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_ref: str
    source_dir: str
    entrypoint: str
    contract_ref: str
    connector: ConnectorBinding
    twin: TwinBinding
    allowed_uri_processes: list[str]
    required_gates: list[str]
    steps: list[PublicationStep]
    manifest_hash: str = ""
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    def canonical_payload(self) -> dict[str, Any]:
        value = self.model_dump(mode="json", by_alias=True, exclude={"created_at", "manifest_hash", "diagnostics"})
        return value

    def compute_hash(self) -> str:
        raw = json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @model_validator(mode="after")
    def fill_hash(self) -> "PublicationPlan":
        computed = self.compute_hash()
        if self.manifest_hash and self.manifest_hash != computed:
            raise ValueError("manifest_hash does not match the canonical publication plan")
        self.manifest_hash = computed
        return self


class GateResult(BaseModel):
    gate: str
    passed: bool
    evidence_step: str | None = None
    message: str


class PublicationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: Literal["wellmanifest.plesk-publication-receipt/v1"] = Field(
        default="wellmanifest.plesk-publication-receipt/v1",
        alias="schema",
        serialization_alias="schema",
    )
    project_id: str
    manifest_hash: str
    mode: Literal["dry-run", "apply"]
    ok: bool
    connector_plan_hash: str | None = None
    gates: list[GateResult] = Field(default_factory=list)
    step_results: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class WorkspaceResolver:
    """Resolve opaque ``workspace:*`` references to allowlisted local directories."""

    def __init__(
        self,
        *,
        mappings: dict[str, str | Path] | None = None,
        workspace_root: str | Path | None = None,
        allowed_source_names: tuple[str, ...] = ("www", "docs", "logo"),
    ) -> None:
        self.mappings = {key: Path(value) for key, value in (mappings or {}).items()}
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self.allowed_source_names = set(allowed_source_names)

    def resolve(self, source_ref: str) -> Path:
        if source_ref in self.mappings:
            candidate = self.mappings[source_ref]
        elif source_ref.startswith("workspace:") and self.workspace_root is not None:
            name = source_ref.split(":", 1)[1]
            candidate = self.workspace_root / name
        else:
            raise PleskConfigurationError(
                f"No local source mapping for {source_ref!r}; provide --source-ref REF=PATH or a workspace root"
            )

        resolved = candidate.expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise PleskConfigurationError(f"Publication source is not an existing directory: {resolved}")
        if self.workspace_root is not None:
            try:
                resolved.relative_to(self.workspace_root)
            except ValueError as exc:
                raise PleskConfigurationError("Publication source escapes the configured workspace root") from exc
        if resolved.name not in self.allowed_source_names:
            raise PleskConfigurationError(
                "Publication source must be named www, docs or logo unless the connector is configured with an explicit allowlist"
            )
        return resolved


class PleskPublicationPlanner:
    def __init__(self, registry: ProjectRegistry, resolver: WorkspaceResolver) -> None:
        self.registry = registry
        self.resolver = resolver

    def build(self, project_id: str) -> PublicationPlan:
        project = self.registry.get(project_id)
        publication = project.publication
        source_dir = self.resolver.resolve(publication.source_ref)
        entrypoint_path = source_dir / project.entrypoint
        diagnostics: list[Diagnostic] = []
        if self.registry.twin.attestation_required and not self.registry.twin.revision:
            diagnostics.append(
                Diagnostic(
                    code="WM-TWIN-101",
                    severity=Severity.WARNING,
                    phase="plan",
                    path="/twin/revision",
                    message=(
                        "The URI Twin baseline is not pinned to an exact verified revision; "
                        "the production control plane must supply and attest one before autonomous apply."
                    ),
                )
            )
        if not entrypoint_path.exists():
            diagnostics.append(
                Diagnostic(
                    code="WM-PLESK-101",
                    severity=Severity.WARNING,
                    phase="plan",
                    path=f"/projects/{project_id}/entrypoint",
                    message=f"Entrypoint {project.entrypoint!r} does not exist under the resolved publication source.",
                )
            )

        common_panel = self._panel_payload(publication)
        host = publication.sftp_host or project.subscription
        sync_payload: dict[str, Any] = {
            "source_dir": str(source_dir),
            "remote_path": publication.remote_path,
            "host": host,
            "domain": project.domain,
            "transport": publication.transport,
            "sftp_port": publication.sftp_port,
            "sftp_vault_entry_id": publication.sftp_vault_entry_id,
            "apply": False,
        }
        self._copy_optional(
            sync_payload,
            publication,
            "credential_origin",
            "host_fingerprint",
            "actor",
            "pack_id",
            "pack_version",
        )

        expected: dict[str, Any] = {
            "dns_targets": [project.origin_ip],
            "tls_hostname": project.domain,
        }
        if publication.verification.content_sha256:
            expected["content_sha256"] = publication.verification.content_sha256
        verify_payload = {
            "hostname": project.domain,
            "origin_ip": project.origin_ip,
            "path": publication.verification.path,
            "expected": expected,
            "expected_https_status": publication.verification.expected_http_status,
            "verification_mode": publication.verification.mode,
            "deployment_ref": publication.deployment_ref,
        }
        if publication.verification.marker:
            verify_payload["expected_marker"] = publication.verification.marker

        steps = [
            PublicationStep(
                id="connector-ready",
                title="Read Plesk connector readiness",
                uri="plesk://host/doctor/query/report",
                mode="query",
                phase="preflight",
                payload={},
                gate="connector_ready",
            ),
            PublicationStep(
                id="subscription-twin-fact",
                title="Observe the subscription as a read-only URI Twin fact",
                uri="plesk://host/subscription/query/snapshot",
                mode="query",
                phase="preflight",
                payload={"subscription": project.subscription, **common_panel},
                depends_on=["connector-ready"],
            ),
            PublicationStep(
                id="site-docroot-twin-fact",
                title="Observe the live site docroot as a read-only URI Twin fact",
                uri="plesk://host/site/query/docroot",
                mode="query",
                phase="preflight",
                payload={"domain": project.domain, **common_panel},
                depends_on=["connector-ready"],
            ),
            PublicationStep(
                id="subscription-capabilities",
                title="Check whether the subscription can host the project domain",
                uri="plesk://host/subscription/query/capabilities",
                mode="query",
                phase="preflight",
                payload={"subscription": project.subscription, **common_panel},
                depends_on=["subscription-twin-fact"],
                gate="subscription_can_create_domain",
            ),
            PublicationStep(
                id="dns-authority",
                title="Observe the authoritative DNS provider and consistency",
                uri="plesk://host/dns/query/authority",
                mode="query",
                phase="preflight",
                payload={"zone": project.dns_zone},
                depends_on=["connector-ready"],
                gate="dns_authority_ready",
            ),
            PublicationStep(
                id="dns-propagation",
                title="Check public DNS propagation for the origin address",
                uri="plesk://host/dns/query/propagation",
                mode="query",
                phase="preflight",
                payload={"host": project.domain, "record_type": "A", "expected_value": project.origin_ip},
                depends_on=["dns-authority"],
                gate="dns_ready",
            ),
            PublicationStep(
                id="tls-probe",
                title="Probe origin TLS without mutation",
                uri="plesk://host/site/command/ssl-ensure",
                mode="dry-run",
                phase="preflight",
                payload={
                    "hostname": project.domain,
                    "origin_ip": project.origin_ip,
                    "provider": "auto",
                    "apply": False,
                    **common_panel,
                },
                depends_on=["dns-propagation"],
                gate="tls_ready",
            ),
            PublicationStep(
                id="publish-dry-run",
                title="Build the connector file/hash plan without uploading",
                uri=publication.publish_uri,
                mode="dry-run",
                phase="plan",
                payload=sync_payload,
                depends_on=["subscription-capabilities", "site-docroot-twin-fact", "dns-propagation", "tls-probe"],
                gate="publish_plan_ready",
            ),
            PublicationStep(
                id="publish-apply",
                title="Apply the exact connector plan after an explicit signed grant",
                uri=publication.publish_uri,
                mode="command",
                phase="apply",
                payload=sync_payload,
                depends_on=["publish-dry-run"],
                mutation=True,
                human_approval=True,
            ),
            PublicationStep(
                id="publish-verify",
                title="Verify DNS, TLS, HTTPS and content fingerprint",
                uri=publication.verify_uri,
                mode="command",
                phase="verify",
                payload=verify_payload,
                depends_on=["publish-apply"],
                gate="publication_verified",
            ),
        ]

        required_gates = list(dict.fromkeys(["connector_ready", *project.gates, "publish_plan_ready"]))
        allowed = list(dict.fromkeys(step.uri for step in steps))
        return PublicationPlan(
            id=f"publication:{project.id}:{publication.deployment_ref}",
            project_id=project.id,
            deployment_ref=publication.deployment_ref,
            source_ref=publication.source_ref,
            source_dir=str(source_dir),
            entrypoint=project.entrypoint,
            contract_ref=self.registry.connector.contract_ref,
            connector=self.registry.connector,
            twin=self.registry.twin,
            allowed_uri_processes=allowed,
            required_gates=required_gates,
            steps=steps,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _copy_optional(target: dict[str, Any], source: PublicationConfig, *fields: str) -> None:
        for field in fields:
            value = getattr(source, field)
            if value is not None:
                target[field] = value

    @staticmethod
    def _panel_payload(publication: PublicationConfig) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for field in ("base_url", "subscription_vault_entry_id", "runtime_vault_entry_id", "vault_url"):
            value = getattr(publication, field)
            if value is not None:
                payload[field] = value
        return payload


class PleskPublicationExecutor:
    def __init__(self, client: UrirunProcessClient) -> None:
        self.client = client

    def dry_run(self, plan: PublicationPlan) -> PublicationReceipt:
        results: dict[str, Any] = {}
        diagnostics = list(plan.diagnostics)
        for step in plan.steps:
            if step.phase not in {"preflight", "plan"}:
                continue
            try:
                response = self.client.execute(
                    step.uri,
                    step.payload,
                    mode=step.mode,
                    allowed_uri_processes=plan.allowed_uri_processes,
                    run_id=f"{plan.project_id}:{step.id}",
                )
                results[step.id] = self._handler_value(response)
            except UrirunError as exc:
                diagnostics.append(
                    Diagnostic(
                        code="WM-PLESK-EXEC-001",
                        severity=Severity.ERROR,
                        phase="execute",
                        path=f"/steps/{step.id}",
                        message=str(exc),
                        details={"status": exc.status, "code": exc.code, "response": exc.details},
                    )
                )
                results[step.id] = {"ok": False, "error": str(exc)}
                break

        gates = self._evaluate_gates(plan, results)
        connector_plan_hash = self._find_plan_hash(results.get("publish-dry-run"))
        if not connector_plan_hash:
            diagnostics.append(
                Diagnostic(
                    code="WM-PLESK-PLAN-001",
                    severity=Severity.ERROR,
                    phase="plan",
                    path="/steps/publish-dry-run",
                    message="The connector dry-run did not return a plan_hash; apply is blocked.",
                )
            )
        ok = bool(connector_plan_hash) and all(gate.passed for gate in gates) and not any(
            item.severity == Severity.ERROR for item in diagnostics
        )
        return PublicationReceipt(
            project_id=plan.project_id,
            manifest_hash=plan.manifest_hash,
            mode="dry-run",
            ok=ok,
            connector_plan_hash=connector_plan_hash,
            gates=gates,
            step_results=results,
            diagnostics=diagnostics,
        )

    def apply(
        self,
        plan: PublicationPlan,
        *,
        plan_hash: str,
        apply_grant: str,
        dry_run_receipt: PublicationReceipt | None = None,
    ) -> PublicationReceipt:
        if not plan_hash or not apply_grant:
            raise PleskConfigurationError("apply requires both the connector plan_hash and a signed apply_grant")
        dry = dry_run_receipt or self.dry_run(plan)
        if not dry.ok:
            raise PleskConfigurationError("publication preflight or dry-run is not green; apply is blocked")
        if dry.manifest_hash != plan.manifest_hash:
            raise PleskConfigurationError("publication plan changed after dry-run")
        if dry.connector_plan_hash != plan_hash:
            raise PleskConfigurationError("apply plan_hash does not match the connector dry-run receipt")

        apply_step = next(step for step in plan.steps if step.phase == "apply")
        verify_step = next(step for step in plan.steps if step.phase == "verify")
        results = dict(dry.step_results)
        diagnostics = list(dry.diagnostics)

        apply_payload = {**apply_step.payload, "apply": True, "plan_hash": plan_hash, "apply_grant": apply_grant}
        try:
            apply_response = self.client.execute(
                apply_step.uri,
                apply_payload,
                mode="command",
                allowed_uri_processes=plan.allowed_uri_processes,
                run_id=f"{plan.project_id}:publish-apply:{plan_hash[:16]}",
            )
            results[apply_step.id] = self._handler_value(apply_response)
            apply_value = results[apply_step.id]
            if not self._is_successful_apply(apply_value):
                raise UrirunError("connector did not report an executed publication", details=apply_value)

            verify_response = self.client.execute(
                verify_step.uri,
                verify_step.payload,
                mode="command",
                allowed_uri_processes=plan.allowed_uri_processes,
                run_id=f"{plan.project_id}:publish-verify:{plan_hash[:16]}",
            )
            results[verify_step.id] = self._handler_value(verify_response)
        except UrirunError as exc:
            diagnostics.append(
                Diagnostic(
                    code="WM-PLESK-APPLY-001",
                    severity=Severity.ERROR,
                    phase="apply",
                    message=str(exc),
                    details={"status": exc.status, "code": exc.code, "response": exc.details},
                )
            )

        verified = self._is_verified(results.get("publish-verify"))
        gates = [*dry.gates, GateResult(
            gate="publication_verified",
            passed=verified,
            evidence_step="publish-verify",
            message="Publication verification passed." if verified else "Publication verification did not return verified evidence.",
        )]
        ok = verified and not any(item.severity == Severity.ERROR for item in diagnostics)
        return PublicationReceipt(
            project_id=plan.project_id,
            manifest_hash=plan.manifest_hash,
            mode="apply",
            ok=ok,
            connector_plan_hash=plan_hash,
            gates=gates,
            step_results=results,
            diagnostics=diagnostics,
        )

    def _evaluate_gates(self, plan: PublicationPlan, results: dict[str, Any]) -> list[GateResult]:
        known: dict[str, GateResult] = {
            "connector_ready": GateResult(
                gate="connector_ready",
                passed=str(self._dict(results.get("connector-ready")).get("status", "")).lower() == "ready",
                evidence_step="connector-ready",
                message="Plesk connector reports ready status.",
            ),
            "subscription_can_create_domain": GateResult(
                gate="subscription_can_create_domain",
                passed=self._dict(results.get("subscription-capabilities")).get("can_create_domain") is True,
                evidence_step="subscription-capabilities",
                message="Subscription reports capacity to create the domain.",
            ),
            "dns_authority_ready": GateResult(
                gate="dns_authority_ready",
                passed=self._dict(self._dict(results.get("dns-authority")).get("authority")).get("consistent") is True,
                evidence_step="dns-authority",
                message="Authoritative DNS observation is consistent.",
            ),
            "dns_ready": GateResult(
                gate="dns_ready",
                passed=(
                    self._dict(results.get("dns-propagation")).get("propagated") is True
                    and self._dict(results.get("dns-propagation")).get("consensus") is True
                ),
                evidence_step="dns-propagation",
                message="Public DNS propagation agrees with the declared origin IP.",
            ),
            "tls_ready": GateResult(
                gate="tls_ready",
                passed=self._tls_ready(results.get("tls-probe")),
                evidence_step="tls-probe",
                message="Origin TLS probe returned usable evidence without mutation.",
            ),
            "publish_plan_ready": GateResult(
                gate="publish_plan_ready",
                passed=bool(self._find_plan_hash(results.get("publish-dry-run"))),
                evidence_step="publish-dry-run",
                message="Connector returned an exact dry-run plan hash.",
            ),
        }
        gates: list[GateResult] = []
        for name in plan.required_gates:
            gates.append(
                known.get(
                    name,
                    GateResult(
                        gate=name,
                        passed=False,
                        message="Unknown project gate; fail-closed until a deterministic evaluator is registered.",
                    ),
                )
            )
        return gates

    @staticmethod
    def _handler_value(response: dict[str, Any]) -> Any:
        result = response.get("result")
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        return result if result is not None else response

    @classmethod
    def _find_plan_hash(cls, value: Any) -> str | None:
        item = cls._dict(value)
        plan_hash = item.get("plan_hash")
        if isinstance(plan_hash, str) and plan_hash:
            return plan_hash
        nested = cls._dict(item.get("plan"))
        nested_hash = nested.get("plan_hash")
        return nested_hash if isinstance(nested_hash, str) and nested_hash else None

    @classmethod
    def _tls_ready(cls, value: Any) -> bool:
        item = cls._dict(value)
        if item.get("ok") is False:
            return False
        probe = cls._dict(item.get("probe"))
        if any(probe.get(key) is True for key in ("valid", "verified", "reachable", "tls_ready", "certificate_valid")):
            return True
        # Some connector probe-only receipts only expose a successful strategy and
        # a dry_run flag.  Treat that as evidence only when the handler itself is ok.
        return item.get("ok") is True and item.get("dry_run") is True and bool(item.get("strategy") or probe)

    @classmethod
    def _is_successful_apply(cls, value: Any) -> bool:
        item = cls._dict(value)
        if item.get("ok") is False:
            return False
        return item.get("executed") is True and item.get("mutation_attempted") is not False

    @classmethod
    def _is_verified(cls, value: Any) -> bool:
        item = cls._dict(value)
        if item.get("ok") is False:
            return False
        if item.get("verified") is True or item.get("status") in {"verified", "ready", "passed"}:
            return True
        checks = item.get("checks")
        if isinstance(checks, list) and checks:
            return all(cls._dict(check).get("ok") is True for check in checks)
        return False

    @staticmethod
    def _dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}


def load_project_registry(path: str | Path) -> ProjectRegistry:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        import yaml

        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    return ProjectRegistry.model_validate(data)

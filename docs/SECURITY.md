# Security model

## Primary rule

WellManifest is a format and capability runtime, **not a generic remote code
execution service**. Remote execution means selecting a preinstalled runtime
profile and invoking a registered concrete URI Process.

## Authority

Authority is resolved in this order:

1. authenticated principal/tenant;
2. server-side Contract AQL reference and revision;
3. requested concrete URI and message kind;
4. runtime/environment policy;
5. adapter-specific preconditions;
6. approval/ticket/receipt gates where required.

A client-side allowlist, type comment, digital twin or LLM result cannot widen
that authority.

## URI rules

- executed URIs must be concrete and contain no `*`;
- wildcard scopes are prefix/exact permissions only;
- missing contract or unmatched scope fails before adapter contact;
- run IDs are length- and character-bounded;
- adapters are registered explicitly;
- mutating adapters should be narrower than query adapters.

## Parser safety

- input/body limits should be set at reverse proxy and application layers;
- YAML uses the safe loader and rejects duplicate keys;
- situation/policy expressions use a whitelisted AST, never `eval`;
- policy DSL is not passed to Bash;
- HCL-lite and proto IR parsers do not evaluate functions or execute plugins;
- schema fetching from arbitrary remote URLs is disabled by default.

## Network safety

The example SOA adapter creates an HTTP plan and does not perform unrestricted
outbound requests. A production HTTP connector must enforce scheme, host, IP
range, DNS rebinding, redirect, method, size and timeout policies.

Raw node endpoints should live on an isolated network and use a dedicated
secret available only to the bridge. Public clients enter through control APIs
that resolve tickets/contracts.

## Secrets

Secrets are referenced, not embedded:

```json
{"credential_ref":"vault://tenant/connectors/plesk"}
```

The runtime must not log secret values. Connector-specific leases should be
short-lived and scoped to the exact operation. Digital twins store no tokens or
vault contents.

## Diagnostics and logs

Diagnostics may contain paths and evidence references but should avoid raw
credentials, authorization headers, local absolute paths and oversized payloads.
Event payload redaction is an adapter responsibility. Stable codes make
failures machine-actionable without relying on LLM interpretation.

## Idempotency and concurrency

The JSONL store is suitable for a local demo, not distributed exactly-once
semantics. Production commands need a transactional idempotency table or event
stream version check. Concurrent retries with the same key must converge on one
accepted result.

## Container hardening checklist

- run as a non-root UID;
- use a read-only root filesystem where practical;
- mount contracts and schemas read-only;
- set CPU/memory/PID limits;
- drop Linux capabilities and disallow privilege escalation;
- isolate node/bridge networks;
- use TLS/mTLS at ingress and broker/gRPC layers;
- pin released images by digest and produce SBOM/provenance;
- do not mount the Docker socket.

The included Compose files are development examples; production overlays must
add secrets, TLS, immutable images and infrastructure-specific controls.

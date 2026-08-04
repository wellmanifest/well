# Plesk publication with WellManifest, URI Twin and urirun

WellManifest turns a `subactor.projects/v1` project registry into a deterministic,
least-privilege publication plan. The integration deliberately separates two
responsibilities:

- `@uri-twin/plesk` is the read-only environment/capability baseline used to
  understand the Plesk surface and to reason about readiness;
- `urirun-connector-plesk` is the effect adapter called through concrete URI
  Processes for observations, dry-run, guarded apply and post-publication
  verification.

The plan obtains the connector's read-only `subactor.twin-fact/v1` observations
for subscription capacity and the live docroot. A platform twin-map consumer can
join them with the reviewed `@uri-twin/plesk` baseline. The baseline remains a
roadmap and evidence source; Contract AQL and the connector remain the authority
and effect boundaries.

The project registry contains no Plesk password, SFTP password, Cloudflare token
or vault secret. It may contain only opaque vault entry IDs and an HTTPS
credential origin. Mutation is disabled by default.

## Source project registry

The minimal registry accepted by WellManifest is the same shape as the project
configuration used by Subactor:

```json
{
  "schema": "subactor.projects/v1",
  "projects": [{
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
      "verification": {"mode": "content_hash", "path": "/"}
    },
    "gates": ["subscription_can_create_domain", "dns_ready", "tls_ready"]
  }]
}
```

Optional top-level `connector` and `twin` objects pin the package/repository,
contract and read-only twin revision. See
[`examples/plesk/projects.extended.yaml`](../examples/plesk/projects.extended.yaml).
 When `attestation_required` is true but `revision` is not
set, planning emits `WM-TWIN-101`; this is acceptable for local preview, while a
production control plane should pin and verify the exact Git revision.

## Deterministic plan

```bash
wellm validate examples/plesk/projects.json \
  --schema schemas/projects.schema.json

wellm plesk-plan examples/plesk/projects.json \
  --project obslugabiurowa-pl \
  --source-ref workspace:obslugabiurowa-pl=examples/plesk/site/www \
  --workspace-root . \
  --to yaml \
  --output .wellm/obslugabiurowa-plan.yaml
```

`source_ref` is an opaque logical reference. The local path is supplied by the
operator or server deployment. The resolver rejects a path outside the declared
workspace root and, in the safe default profile, accepts only source directories
named `www`, `docs` or `logo`.

The generated plan contains only concrete URI Processes:

| Phase | URI Process | Purpose | Mutation |
|---|---|---|---:|
| preflight | `plesk://host/doctor/query/report` | connector readiness | no |
| preflight | `plesk://host/subscription/query/snapshot` | read-only subscription twin fact | no |
| preflight | `plesk://host/site/query/docroot` | read-only live docroot twin fact | no |
| preflight | `plesk://host/subscription/query/capabilities` | subscription capacity | no |
| preflight | `plesk://host/dns/query/authority` | DNS authority consistency | no |
| preflight | `plesk://host/dns/query/propagation` | public A-record consensus | no |
| preflight | `plesk://host/site/command/ssl-ensure` with `apply=false` | TLS probe | no |
| plan | `plesk://host/site/command/sync` with `apply=false` | file/hash plan | no |
| apply | `plesk://host/site/command/sync` with `apply=true` | exact guarded upload | **yes** |
| verify | `plesk://host/site/command/publish-verify` | DNS/TLS/HTTPS/content evidence | no expected mutation |

The plan includes a deterministic `manifest_hash`. The connector dry-run must
add its own `plan_hash`. Apply is accepted only when both hashes still refer to
the reviewed plan.

## Dry-run and apply

Trusted operator or integration environment:

```bash
export URIRUN_NODE_URL=http://urirun-bridge:8080
export URIRUN_TOKEN='read-from-secret-store'

wellm plesk-publish examples/plesk/projects.extended.yaml \
  --project obslugabiurowa-pl \
  --source-ref workspace:obslugabiurowa-pl=examples/plesk/site/www \
  --workspace-root . \
  --node-url "$URIRUN_NODE_URL" \
  --output .wellm/obslugabiurowa-dry-run.json
```

The command above performs preflight and connector dry-run only. It returns a
receipt with `ok`, evaluated gates and `connector_plan_hash`.

Apply is a separate command:

```bash
export URIRUN_APPLY_GRANT='signed-single-use-grant'

wellm plesk-publish examples/plesk/projects.extended.yaml \
  --project obslugabiurowa-pl \
  --source-ref workspace:obslugabiurowa-pl=examples/plesk/site/www \
  --workspace-root . \
  --node-url "$URIRUN_NODE_URL" \
  --apply \
  --plan-hash "$CONNECTOR_PLAN_HASH" \
  --output .wellm/obslugabiurowa-apply-receipt.json
```

The executor blocks apply when:

- any required gate is not green;
- the dry-run did not return `plan_hash`;
- the local plan changed after dry-run;
- the supplied hash differs from the connector receipt;
- the signed grant is missing;
- the connector does not report an executed mutation;
- final publication verification is not green.

The connector is still responsible for its own environment gates, one-time grant
verification, vault leases and plan-hash enforcement. WellManifest adds an
independent orchestration guard; it does not replace connector security.

## Production Subactor boundary

For an autonomous Subactor deployment, untrusted callers should not receive a
raw `urirun-node` endpoint or connector credential. The recommended path is:

```text
project registry
      │
      ▼
WellManifest plan + schema validation
      │
      ▼
Subactor Control: ticket / AQL / idempotency / approval
      │
      ▼
Bridge: re-read contract and exact URI at effect boundary
      │
      ▼
urirun-connector-plesk
      │
      ▼
receipt + publication verification + event log
```

The `UrirunProcessClient` may point at a trusted bridge exposing the canonical
`POST /run` contract. Direct-node use is intended for controlled operations and
integration tests, not for browser or autonomous public callers.

## HTTP service

The WellManifest service can build plans without enabling any remote execution:

```bash
export WELLMANIFEST_WORKSPACE_ROOT="$PWD/examples/plesk/site"
wellm serve --port 8080
```

```bash
curl -fsS http://localhost:8080/v1/plesk/plan \
  -H 'content-type: application/json' \
  --data @- <<'JSON'
{
  "config": {
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
          "verification": {"mode": "content_hash", "path": "/"}
        },
        "gates": ["subscription_can_create_domain", "dns_ready", "tls_ready"]
      }
    ]
  },
  "project_id": "obslugabiurowa-pl",
  "source_refs": {
    "workspace:obslugabiurowa-pl": "obslugabiurowa-pl/www"
  }
}
JSON
```

Remote publication through `/v1/plesk/publish` is disabled unless the service
operator sets `WELLMANIFEST_ENABLE_PLESK_EXECUTION=1`. The apply grant is sent
as `x-urirun-apply-grant`; it must never be stored in the registry.

## JavaScript / TypeScript

```js
import {
  buildPleskPublicationPlan,
  validateProjectRegistry,
  WellManifestClient,
} from "@wellmanifest/wellm-sdk";

const registry = validateProjectRegistry(projects);
const plan = await buildPleskPublicationPlan(registry, {
  projectId: "obslugabiurowa-pl",
  sourceRefs: {
    "workspace:obslugabiurowa-pl": "/workspace/obslugabiurowa-pl/www",
  },
});

const client = new WellManifestClient({baseUrl: "http://localhost:8080"});
const remotePlan = await client.planPlesk({
  config: registry,
  project_id: "obslugabiurowa-pl",
  source_refs: {"workspace:obslugabiurowa-pl": "obslugabiurowa-pl/www"},
});
```

The TypeScript dialect is also available for round-trippable generated data:

```bash
wellm convert examples/plesk/projects.json --from json --to typescript \
  --output examples/plesk/projects.wm.ts
```

It is a restricted data module, not an arbitrary TypeScript evaluator.

## Docker Compose sidecar

A minimal sidecar is included as
[`compose.plesk.example.yml`](../compose.plesk.example.yml):

```bash
docker compose -f compose.plesk.example.yml up --build wellm
```

The site source is mounted read-only. Connector and vault secrets are not placed
in Compose. Production should attach the trusted bridge/node on a private
network and inject secrets using the infrastructure secret manager.

## Schemas and receipts

- [`schemas/projects.schema.json`](../schemas/projects.schema.json)
- [`schemas/publication-plan.schema.json`](../schemas/publication-plan.schema.json)
- [`schemas/publication-receipt.schema.json`](../schemas/publication-receipt.schema.json)

Every failure is returned as a structured `ERROR`, `WARNING` or `INFO`
diagnostic. Unknown project gates fail closed until a deterministic evaluator is
registered.

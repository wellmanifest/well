# HTTP API reference

The generated OpenAPI document is [`schemas/openapi.json`](../schemas/openapi.json).

## Authentication headers

Development can run without a token. When `WELLMANIFEST_TOKEN` is set, send one
of the compatibility headers accepted by the reference gateway:

```text
x-wellmanifest-token: <token>
```

or:

```text
x-urirun-token: <token>
```

Production should terminate TLS and bind principals/contracts through an
identity-aware gateway. The reference token is a deployment guard, not a full
identity system.

## Discovery

```text
GET /healthz
GET /v1/capabilities
GET /v1/dialects
GET /v1/runtimes
GET /v1/versions
GET /v1/env-contract
```

`/v1/capabilities` includes the Plesk publication and LLM benchmark extension
metadata exposed by the current runtime.

## Convert

`POST /v1/convert`

```json
{
  "source": "status:\n  value: SUCCEEDED\n",
  "source_dialect": "yaml",
  "target_dialect": "json",
  "projection": "data",
  "schema": null,
  "type_mode": "preserve"
}
```

The response contains `output`, selected dialects, conversion lossiness and
structured diagnostics. `type_mode` is `preserve`, `schema`, `infer` or `none`
when the target is typed Wellm.

## Validate

`POST /v1/validate`

```json
{
  "source": {
    "status": {
      "operation": "002-cv-pdf2md",
      "value": "SUCCEEDED",
      "errors": []
    }
  },
  "dialect": "json",
  "schema": {"type": "object"}
}
```

## Analyze intent represented in multiple formats

`POST /v1/intent/analyze`

```json
{
  "representations": [
    {"id": "json", "dialect": "json", "source": "{\"schema\":\"example/v1\"}"},
    {"id": "yaml", "dialect": "yaml", "source": "schema: example/v1\n"}
  ],
  "schema": {"type": "object", "required": ["schema"]}
}
```

The response is `wellm.intent-format-analysis/v1`: exact hashes, semantic
hashes, schema results and pairwise structural diffs. File-based projects use
the richer `wellm intent analyze` CLI, which can also emit todo2code evidence.

## Execute a registered URI Process

`POST /v1/runtime/execute`

```json
{
  "uri": "youtube://channel/video/query/list",
  "payload": {"channel": "ours"},
  "contract_ref": "contract:dev",
  "run_id": "ticket-002:youtube:1",
  "runtime": {
    "runtime_ref": "runtime:backend-python@1",
    "environment": "backend",
    "execution": "local"
  }
}
```

The response contains result, diagnostics, run/correlation information and event
receipts.

## Build a Plesk publication plan

`POST /v1/plesk/plan`

The server must have a trusted, read-only workspace root:

```bash
export WELLMANIFEST_WORKSPACE_ROOT=/srv/wellm-workspaces
```

Request:

```json
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
```

Paths in `source_refs` are resolved under `WELLMANIFEST_WORKSPACE_ROOT`; escaping
the root is rejected.

## Execute a Plesk dry-run or apply

`POST /v1/plesk/publish`

This endpoint is disabled by default. The server operator must explicitly set:

```bash
export WELLMANIFEST_ENABLE_PLESK_EXECUTION=1
```

A dry-run request adds:

```json
{
  "node_url": "http://urirun-bridge:8080",
  "contract_ref": "contract:plesk-publication",
  "apply": false
}
```

For apply, send:

```text
x-urirun-token: <bridge token>
x-urirun-apply-grant: <signed single-use grant>
```

and include:

```json
{
  "apply": true,
  "plan_hash": "<exact connector dry-run hash>"
}
```

The endpoint performs a fresh preflight/dry-run and requires the returned hash
to match before it sends the apply request.

## Envelope exchange

`POST /v1/envelopes` accepts the canonical envelope. The operation selects the
registered handler, `accept` drives output negotiation, and diagnostics are
returned in a result envelope.

## Compatibility `/run`

The `UrirunProcessClient` posts:

```json
{
  "uri": "youtube://channel/video/query/list",
  "mode": "execute",
  "payload": {}
}
```

Headers may include `x-urirun-token`, `x-urirun-run-id` and
`x-wellmanifest-contract`. This endpoint is convenient for trusted integration.
Managed autonomy should use the Control/Bridge flow described in
[`URI_PROCESS.md`](URI_PROCESS.md).

## Events and WebSocket

```text
GET /v1/events?stream=<optional>&after=0&limit=100
WS  /v1/ws?token=<optional>
```

The WebSocket subprotocol is `wellmanifest.v1`. Supported operations include `convert`, `validate`, `execute`, `exchange`,
`format`, `semantic-diff`, `versions`, `env-contract` and `intent-analyze`.

## Format profiles

```text
GET /v1/profiles
POST /v1/format
POST /v1/semantic-diff
```

Format request:

```json
{
  "value": {"b": 2, "a": 1},
  "profile": "wire-json@1",
  "schema": null
}
```

The response includes the selected profile, `semanticSha256` and formatted
output. `semantic-diff` accepts `left` and `right` JSON-compatible values and
returns `wellm.semantic-diff/v1`.

WebSocket operations additionally include `format` and `semantic-diff`.

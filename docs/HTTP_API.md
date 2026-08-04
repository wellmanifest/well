# HTTP API reference

## Authentication headers

Development can run without a token. When `WELLMANIFEST_TOKEN` is set, send:

```text
Authorization: Bearer <token>
```

or the configured compatibility header. Production should terminate TLS and
bind principals/contracts through an identity-aware gateway.

## Convert

`POST /v1/convert`

```json
{
  "source": "status:\n  value: SUCCEEDED\n",
  "source_dialect": "yaml",
  "target_dialect": "json",
  "projection": "data",
  "schema": null
}
```

Response contains `output`, normalized `document`, conversion quality and
diagnostics.

## Validate

`POST /v1/validate`

```json
{
  "source": {"status":{"operation":"002-cv-pdf2md","value":"SUCCEEDED","errors":[]}},
  "source_dialect": "json",
  "schema": {"type":"object"}
}
```

## Execute

`POST /v1/runtime/execute`

```json
{
  "uri": "youtube://channel/video/query/list",
  "payload": {"channel":"ours"},
  "contract_ref": "contract:dev",
  "run_id": "ticket-002:youtube:1",
  "runtime_ref": "runtime:backend-python@1",
  "environment": "backend"
}
```

The response includes result, diagnostics, run/correlation information and
idempotency status.

## Envelope exchange

`POST /v1/envelopes` accepts the canonical envelope. The operation selects the
handler, `accept` drives output negotiation, and diagnostics are returned in a
result envelope.

## Compatibility `/run`

The supplied `UrirunProcessClient` posts:

```json
{"uri":"youtube://channel/video/query/list","mode":"execute","payload":{}}
```

Headers may include `x-urirun-token`, `x-urirun-run-id` and contract reference.
This endpoint is convenient for migration. Managed autonomy should use the
control/bridge flow described in `URI_PROCESS.md`.

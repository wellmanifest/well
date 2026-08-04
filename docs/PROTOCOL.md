# Protocol and content negotiation

## Envelope overview

The canonical wire object is `wellmanifest.protocol/v1`. JSON Schema lives in
`schemas/envelope.schema.json`; protobuf definitions live in
`proto/wellmanifest/v1/wellmanifest.proto`.

```json
{
  "spec": "wellmanifest.protocol/v1",
  "id": "01J...",
  "correlation_id": "ticket-002",
  "kind": "command",
  "operation": "wellmanifest://runtime/convert/execute",
  "content_type": "yaml",
  "accept": ["json", "proto3"],
  "schema_ref": "schema:status@1",
  "contract_ref": "contract:frontend-demo",
  "idempotency_key": "ticket-002:convert:1",
  "runtime": {
    "runtime_ref": "runtime:backend-python@1",
    "environment": "backend",
    "execution": "remote"
  },
  "payload": {
    "source": "status:\n  value: SUCCEEDED\n",
    "source_dialect": "yaml",
    "target_dialect": "json"
  },
  "metadata": {}
}
```

## Message kinds

| Kind | Meaning |
|---|---|
| `command` | Requests a state-changing or operational action. |
| `query` | Requests a read-only result. |
| `event` | Announces an immutable fact. |
| `result` | Terminal or intermediate response to a command/query. |
| `diagnostic` | Carries validation or runtime diagnostics. |

The runtime can reject an operation whose URI semantics conflict with the
message kind.

## Negotiation algorithm

1. Read the source `content_type` and ordered receiver `accept` list.
2. Prefer an exact supported match.
3. Otherwise find a registered conversion path.
4. Parse to a `Document` and validate before emission when a schema is present.
5. Emit the first acceptable target and report conversion quality.
6. Return `WM-NEGOTIATE-*` or `WM-CONVERT-*` diagnostics if no safe path exists.

Conversion quality is one of:

- `LOSSLESS` — all represented semantics can be reconstructed;
- `NORMALIZED` — semantics are retained but formatting/comments/order may
  change;
- `LOSSY` — explicitly accepted information is omitted;
- `UNSUPPORTED` — no declared mapping exists.

JSON ↔ YAML in the JSON-compatible profile is normally normalized. Policy DSL
or proto3 to plain JSON is lossy unless the caller asks for the IR projection.

## Schema references

A schema may be provided inline for development or referenced by an immutable
identifier. Production services should resolve only trusted schemes such as:

```text
schema:status@1
sha256:<digest>
registry://tenant/schema/status/1
```

The reference implementation accepts a local schema object/path through its
CLI and API. A network schema registry is an extension point; arbitrary URL
fetching is deliberately not enabled.

## Correlation, causation and idempotency

`correlation_id` groups a business flow. `causation_id` points at the message or
event that caused the current message. `idempotency_key` identifies one
logical effect attempt.

A runtime must not silently repeat a completed mutation for the same key. The
reference runtime returns the established result and records the event history.

## Error model

A response may carry multiple diagnostics:

```json
{
  "code": "WM-SCHEMA-001",
  "severity": "ERROR",
  "message": "'COMPLETED' is not one of the allowed states",
  "phase": "schema",
  "path": "/status/value",
  "schema_path": "/$defs/Status/properties/value/enum",
  "hint": "Use PENDING, RUNNING, SUCCEEDED or FAILED"
}
```

`ERROR` means the requested phase failed. `WARNING` means a usable result exists
but is non-canonical, normalized or potentially lossy. `INFO` records evidence,
selected runtime, conversion path or successful validation.

## Versioning

The `spec` major version is compatibility-breaking. Dialects are independently
versioned (`typed@1`, `policy-sh@1`). Runtime implementations advertise their
supported versions through `/v1/capabilities` and the gRPC capabilities call.

Unknown metadata must never grant authority. Unsupported required fields or
major versions fail closed.

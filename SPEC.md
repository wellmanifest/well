# WellManifest Protocol 0.1

Status: **experimental**. Normative key words in this document use their common
RFC-style meanings.

## 1. Protocol identity

A protocol message MUST declare:

```json
{"spec": "wellmanifest.protocol/v1"}
```

A receiver MUST reject unsupported major versions. Minor extensions MUST remain
backward-compatible and unknown metadata MUST NOT grant authority.

## 2. Envelope

The canonical envelope contains identity, correlation, kind, concrete operation
URI, source content type, acceptable response formats, schema and contract
references, idempotency key, runtime target, payload, diagnostics and metadata.
The JSON Schema is `schemas/envelope.schema.json`; protobuf identity is
`wellmanifest.v1.Envelope`.

## 3. Content negotiation

The sender declares `content_type`; the receiver declares ordered `accept`.
A gateway MAY convert when both dialects have a defined mapping. It MUST report
one of `LOSSLESS`, `NORMALIZED`, `LOSSY`, or `UNSUPPORTED`.

`data` projection contains only JSON-compatible values. `ir` projection
contains declarations, types, rules, services and source metadata needed for a
round trip.

## 4. URI Process

An executable operation MUST match:

```text
scheme://target/package/resource/operation
```

It MUST be concrete. `*` MAY occur in capability contracts but MUST NOT occur in
an executed address. The runtime MUST authorize the concrete URI before
contacting an adapter.

## 5. Diagnostics

Every diagnostic MUST contain `code`, `severity` and `message`. Severity is one
of `ERROR`, `WARNING`, `INFO`. An `ERROR` makes the relevant phase unsuccessful;
a `WARNING` preserves a result but identifies a non-canonical or lossy aspect;
an `INFO` records evidence or successful validation.

## 6. Events

Commands and executions SHOULD append requested and terminal events with
correlation and causation identifiers. Reusing an idempotency key MUST return
the established result or a conflict; it MUST NOT silently repeat a mutation.

## 7. Runtime targets

A target declares `runtime_ref`, `environment`, `execution` and bounded
resources. Remote targets invoke registered declarative processes. They do not
imply arbitrary code upload or execution.

## 8. Security

Authority comes from a server-resolved contract. A client-side allowlist is only
an early rejection optimization. Digital twins and LLM outputs MUST NOT expand
contract authority. Side effects SHOULD require application-specific tickets,
approvals and receipts.

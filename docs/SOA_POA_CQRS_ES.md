# SOA, POA, CQRS and Event Sourcing

## Service-oriented use

In SOA mode, a WellManifest URI Process represents a stable service capability
rather than an implementation language. A caller can describe a request in
YAML, receive JSON, and let the gateway negotiate the representation.

```yaml
spec: wellmanifest.protocol/v1
kind: command
operation: soa://catalog/http/request/plan
contract_ref: contract:dev
payload:
  method: POST
  service: inventory
  path: /v1/items/search
  body:
    query: sensor
```

The built-in example produces a validated request **plan**. An application
adapter may later map the plan to an HTTP client with explicit host allowlists,
timeouts and response limits. The reference runtime does not provide unrestricted
outbound HTTP, avoiding an implicit SSRF proxy.

## Process-oriented use

POA represents work as concrete URI Processes and dependency graphs:

```text
inventory://plesk/capability/query/snapshot
             |
             v
situation://profile/evaluate/query
             |
             v
plesk://host/domain/command/ensure
             |
             +--> cloudflare://zone/dns/command/ensure
             +--> plesk://host/tls/command/ensure
             +--> plesk://host/content/command/deploy
```

Each step has an owner, contract, evidence requirements, idempotency key and
terminal receipt. Wildcard scopes describe permission; DAG nodes always use
concrete URIs.

## CQRS

Commands and queries use the same envelope but remain distinct:

```json
{
  "kind": "command",
  "operation": "ticket://plan/task/command/create",
  "idempotency_key": "PLF-1300:create:1",
  "payload": {"title": "Prepare public-site bootstrap"}
}
```

```json
{
  "kind": "query",
  "operation": "ticket://plan/task/query/get",
  "payload": {"ticket_id": "PLF-1300"}
}
```

A command handler validates authority and invariants, then emits facts. A query
handler reads a projection and must not mutate source state.

## Event Sourcing

The reference implementation appends JSONL events such as:

```json
{"type":"ProcessRequested","run_id":"PLF-1300:step-1","uri":"flow://host/remote-access/query/preflight"}
{"type":"ProcessCompleted","run_id":"PLF-1300:step-1","result":{"ready":true}}
```

This demonstrates correlation, replay and receipts. Production installations
should replace the local JSONL store with a durable append-only database or
message log and implement optimistic concurrency/stream versions.

## Protobuf mapping

The protobuf `Envelope` transports commands, queries, events and results. Domain
services may define specialized protobuf messages and embed or reference them
from the payload. Field numbers and service definitions remain in the protobuf
contract/descriptor rather than being flattened into ordinary JSON.

## Queue mapping

A queue deployment can map:

```text
wellmanifest.command.{tenant}.{bounded-context}
wellmanifest.event.{tenant}.{bounded-context}
wellmanifest.query.{tenant}.{bounded-context}
wellmanifest.result.{tenant}.{correlation-id}
```

MQTT uses hierarchical topics; enterprise brokers may use equivalent routing
keys. Consumers must still validate envelope version, schema and contract.
Transport ACLs complement but do not replace URI Process authorization.

## Saga/process manager

A long process stores explicit state:

```json
{
  "process_id": "public-site-bootstrap:PLF-1300",
  "status": "WAITING_FOR_APPROVAL",
  "steps": [
    {"id":"inventory","status":"DONE","receipt":"event:101"},
    {"id":"dns","status":"READY","depends_on":["inventory"]},
    {"id":"tls","status":"BLOCKED","human_approval":true}
  ]
}
```

Retries use the same logical idempotency key or a versioned attempt according to
the connector contract. Compensation must be an explicit URI Process; it is
never inferred from a name.

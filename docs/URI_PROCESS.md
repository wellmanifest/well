# URI Process and Contract AQL

## Three layers

WellManifest follows the supplied Subactor separation:

1. **Contract AQL** describes who may act and the permitted boundaries, for
   example `ALLOW URI_PROCESS youtube://*`.
2. **OQL** describes the requested business operation such as `process.run` or
   `task.create`.
3. **URI Process** identifies the concrete execution step, for example
   `youtube://channel/moderation/query/pending`.

A wildcard is a capability pattern, never an executable address.

## Canonical address

```text
scheme://target/package/resource/operation
```

The runtime rejects whitespace and `*` in an executed URI. Examples:

```text
youtube://channel/video/query/list
flow://host/remote-access/query/preflight
plesk://host/mailbox/query/status
gpio://rpi/pin/configure/plan
```

## Ticket before effect

For a managed autonomous flow, the production invariant is:

1. a ticket/plan exists before execution;
2. it carries a process manifest with an AQL, EQL, OQL or concrete URI
   definition;
3. the requested step matches that definition;
4. an idempotency key binds ticket and step;
5. the bridge writes a terminal result/receipt and log reference back to the
   same ticket;
6. the controller closes or fails the aggregate plan only after all required
   receipts are present.

The reference runtime models contract checks, idempotency and events. Project
specific ticket, approval and receipt adapters remain integration points.

## Control, bridge and node

```text
client/autonomy
      |
      | OQL + ticket/contract reference
      v
control plane ---- validates plan and derives minimum URI scope
      |
      | concrete URI + ticket/process/idempotency
      v
bridge ----------- repeats authorization at last effect boundary
      |
      v
registered node adapter
```

A raw node `/run` endpoint is infrastructure transport, not an autonomy entry
point. In production it should be isolated, authenticated with a dedicated
secret and reachable only by the bridge. The compatibility endpoint in this
MVP exists for development and must be protected by deployment configuration.

## JavaScript client

```js
import {UrirunProcessClient} from "@wellmanifest/wellm-sdk";

const client = new UrirunProcessClient({
  nodeUrl: "http://localhost:8080",
  contractRef: "contract:dev",
});

const result = await client.execute(
  "youtube://channel/video/query/list",
  {channel: "ours"},
  {
    allowedUriProcesses: ["youtube://*"],
    runId: "ticket-002:youtube-list:1",
  },
);
```

The local `allowedUriProcesses` check prevents an unnecessary request. It does
not grant server authority. The server resolves `contractRef` and must reject a
URI outside that contract.

## Idempotency

`runId` must match the safe identifier grammar and should be derived from:

```text
{ticket}:{process-step}:{attempt-or-version}
```

Replaying the same completed key returns the established result. A conflicting
payload should be rejected by a production idempotency store; the JSONL MVP
shows the event pattern but is not a distributed consensus store.

## Registration

Adapters are registered in process tables instead of dynamically executing
source code:

```python
runtime.register_process(
    "youtube://channel/video/query/list",
    handler,
    read_only=True,
)
```

The handler receives validated payload and context. It returns a JSON-compatible
value or structured diagnostics. Wildcard registrations should be avoided at
the final adapter boundary.

## Denials

Typical stable diagnostics:

| Code | Meaning |
|---|---|
| `WM-URI-001` | URI is not concrete or has invalid syntax. |
| `WM-AUTH-001` | Contract does not allow the URI. |
| `WM-RUN-001` | No registered adapter exists. |
| `WM-IDEMPOTENCY-001` | Run ID is invalid or conflicts. |
| `WM-RUNTIME-001` | Requested runtime/environment is unavailable. |

All denials happen before contacting an external connector.

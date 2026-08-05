# Architecture

## Objective

WellManifest separates **surface syntax**, **canonical meaning**, **transport**
and **execution authority**. A JSON producer, an HCL tool, a browser, a
Raspberry Pi and a policy repository can therefore exchange the same logical
message without pretending that their grammars are identical.

```text
                 authoring and interchange dialects
 JSON  YAML  TOML  HCL  typed@1  policy-sh@1  proto3
   \     |     |    |       |          |          /
    +----+-----+----+-------+----------+---------+
                            |
                    Dialect Registry
           parse / normalize / emit / diagnostics
                            |
                 Document IR + data projection
                            |
          +-----------------+-------------------+
          |                 |                   |
   JSON Schema 2020-12   Type checker     Semantic validators
          |                 |                   |
          +-----------------+-------------------+
                            |
                  WellManifest Envelope v1
           identity, contract, schema, runtime target,
          correlation, idempotency, accept, diagnostics
                            |
       +--------------------+------------------------+
       |                    |                        |
   HTTP / WebSocket      MQTT v5                  gRPC
       |                    |                        |
       +--------------------+------------------------+
                            |
             capability-checked URI Process router
                            |
      frontend | backend | firmware | digital twin | service
```

## Components

### Python reference runtime

`src/wellmanifest/` is the executable reference implementation. It provides the
CLI, parser registry, JSON Schema validation, HTTP/WebSocket service, URI
Process router, event store, situation evaluator and clients. It is deliberately
readable so that protocol semantics can be inspected independently of native
bindings.

### Rust core and generated runtimes

`crates/wellmanifest-core` contains the native data/envelope foundation. The
workspace adds:

- `wellmanifest-cli` for a native command line;
- `wellmanifest-wasm` for browser and edge WASM;
- `wellmanifest-python` for PyO3 acceleration;
- `wellmanifest-node` for a Node-API module.

Version 0.2.0rc4 still treats these crates as build scaffolds. The Python reference
implementation remains the conformance oracle until parser and validator parity
is demonstrated by differential tests.

### JavaScript SDK

`packages/js` is dependency-free and works in modern browsers and Node. It can
use the remote runtime over HTTP or WebSocket and contains the fail-closed
`UrirunProcessClient`.

### Thin firmware clients

Firmware does not need a full compiler. A constrained device can construct a
small envelope, publish it over MQTT or HTTP, and ask a nearby edge/server
runtime to parse, validate, convert or execute a registered URI Process.
Examples are supplied for CPython/Raspberry Pi, MicroPython and a compact C
header.

### Protocol gateway

The gateway exposes the same operations over several transports. Transport is
not authority: every executable request is resolved to a server-side contract
and a concrete URI before an adapter is called.

## Internal models

### Document

A `Document` contains:

- source dialect and document kind;
- JSON-compatible data projection, when available;
- richer IR for declarations, policy rules, services and source metadata;
- type hints and source name;
- diagnostics.

### Envelope

An `Envelope` adds message identity, correlation/causation, operation URI,
content negotiation, schema and contract references, runtime target,
idempotency key, payload and diagnostics.

### Runtime target

A runtime descriptor identifies an environment and execution mode:

```json
{
  "runtime_ref": "runtime:firmware-thin@1",
  "environment": "firmware",
  "execution": "remote",
  "resources": {"memory_kib": 128, "timeout_ms": 5000}
}
```

The descriptor selects a compatible implementation; it never grants additional
permissions.

## Data and IR projections

`projection=data` emits ordinary values suitable for application exchange.
Types, comments, policy rules and protobuf services are intentionally omitted.

`projection=ir` emits a tagged model capable of retaining those constructs. A
policy or `.proto` document should use IR when round-trip fidelity matters.

## Control plane and data plane

The **control plane** manages contracts, runtime profiles, schemas, digital-twin
portraits and process registrations. The **data plane** transports envelopes and
executes already-authorized operations.

A production installation should keep contract mutation outside the public
execution API. The sample configuration is static JSON mounted read-only into
the container.

## Extension points

A new dialect implements `parse()` and `emit()` and declares supported
projections. A new transport maps its correlation and reply semantics to the
envelope. A new URI adapter registers one or more concrete patterns and must
return structured results and diagnostics. A new schema dialect converts to, or
validates against, the canonical type/data model.

## Trust boundaries

```text
untrusted input
     |
     v
size limits -> parser -> schema/type validation -> contract resolution
                                                |
                                                v
                                       concrete URI check
                                                |
                                                v
                                      registered adapter only
                                                |
                                                v
                                  receipt + append-only event
```

No parser, LLM response, digital twin or client-provided wildcard may widen the
server-resolved authority.

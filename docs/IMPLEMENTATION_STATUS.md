# Implementation status and limitations

## Implemented and locally exercised

- Python 3 reference package and CLI;
- JSON, JSON-compatible YAML and TOML import/export;
- HCL-like data blocks and all four requested status forms;
- typed hints/declarations represented in document IR;
- procedural policy parser, including extraction from Markdown `dsl` blocks;
- basic proto3 message/service IR parser;
- JSON Schema Draft 2020-12 validation;
- standardized `ERROR`, `WARNING`, `INFO` diagnostics;
- concrete URI validation and server-side contract scopes;
- idempotent URI Process execution and JSONL events;
- situation-profile metrics/assessments used by the supplied example;
- read-only digital-twin routing demo;
- FastAPI HTTP and WebSocket endpoints;
- dependency-free browser/Node client and URI Process client;
- static landing page source;
- local Python and Node test suites (23 Python tests and 4 Node tests);
- local HTTP/Node/RPi/event-log E2E workflow.

## Supplied as build/integration source

- MQTT v5 bridge using Paho MQTT;
- protobuf/gRPC service and generated-stub workflow;
- Rust core/CLI;
- WASM, PyO3 and N-API crates;
- multi-service Docker and E2E environments;
- RPi/MicroPython/C thin clients;
- CI matrices.

These components require their toolchains/containers and are not claimed as
locally executed in the generated package environment.

## Deliberate limits

### No arbitrary remote code execution

A runtime profile selects an installed implementation. It does not accept
arbitrary source archives, shell fragments or binaries. New application logic
is installed as a reviewed adapter/container and invoked by a concrete URI.

### HCL subset

The Python parser handles the examples and data subset but does not evaluate the
full HCL expression language. Use existing HCL tools for authoritative
application semantics and treat WellManifest as an import/export/schema layer.

### Proto3 subset

The basic parser extracts common messages, fields, services and RPCs. Production
builds generate a `FileDescriptorSet` with `protoc`; descriptors are the
lossless proto IR.

### YAML profile

Only JSON-compatible maps/lists/scalars are portable across all target formats.
Custom tags, cyclic aliases and non-string map keys require a specialized
plugin and IR representation.

### Distributed events

The JSONL store is a transparent demonstration, not a clustered event store.
Production deployments need transactional idempotency, stream concurrency,
retention and access control.

### LLM

The bundled planner is deterministic/mock. Provider credentials and APIs are
not included. Any provider output remains untrusted until parsed, validated and
authorized.

## Definition of stable 1.0

- published protocol/IR conformance vectors;
- differential HCL and proto tests;
- Rust feature parity for the stable data/schema subset;
- reproducible multi-architecture images and signed packages;
- durable event/idempotency adapter contract;
- authenticated contract/schema registry;
- MQTT/gRPC interoperability suites;
- security review and threat-model verification;
- explicit compatibility and deprecation policy.

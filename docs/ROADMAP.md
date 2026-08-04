# Roadmap

## 0.1 — reference package

- common envelope, diagnostics and runtime descriptors;
- Python reference runtime and JS client;
- JSON/YAML/TOML and four status syntaxes;
- policy and proto IR import;
- schema validation, URI authorization, events and situation profiles;
- Docker/CI/native-runtime scaffolding and documentation.

## 0.2 — canonical IR and compiler

- publish `wellmanifest.ir/v1` JSON Schema and protobuf descriptors;
- complete typed AST, nested types, unions, constraints and schema generation;
- formatter and source maps;
- conversion quality proofs and golden vectors;
- plugin manifest/signature format.

## 0.3 — native parity

- move stable parser/validator semantics into Rust core;
- Python and Node use PyO3/N-API by default with reference fallback;
- browser WASM package and size profiles;
- ARM64/RPi releases and benchmarks.

## 0.4 — transport interoperability

- generated gRPC clients and streaming conformance;
- MQTT v5 request/response, QoS and reconnect suite;
- optional Kafka/NATS/AMQP adapters using the same envelope;
- OpenTelemetry trace/correlation mapping.

## 0.5 — orchestration

- durable command/event adapters;
- process DAG/saga state and receipts;
- Contract AQL registry and signed revisions;
- EQL evidence adapters;
- digital-twin lifecycle, false-ready projection and router audit.

## 0.6 — schema and dialect ecosystem

- authoritative HCL bridge/differential tests;
- `protoc` descriptor round-trip and ProtoJSON profiles;
- OpenAPI/AsyncAPI/Avro/CBOR/MessagePack plugins;
- hardware description and constrained binary profile.

## 1.0 — stable protocol

- independent implementations passing conformance;
- security review;
- stable versioning/deprecation commitments;
- signed packages/images, SBOM and reproducible builds;
- production registry, multi-tenant policy and operational guides.

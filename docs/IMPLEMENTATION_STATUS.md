# Implementation status — 0.2.0rc3

## Working reference implementation

The following components are implemented in Python/JavaScript and covered by
local tests:

- JSON, YAML, TOML, HCL-shaped, typed and restricted TypeScript data parsing;
- procedural policy import to structured IR;
- four requested status syntaxes;
- JSON Schema Draft 2020-12 validation;
- named governance formatting profiles (`repo-json@1`, `wire-json@1`, `yaml-json@1` and others);
- deterministic governance build/check with metadata and source-map sidecars;
- exact-byte and semantic SHA-256 digests;
- structural semantic diff and multi-dialect round-trip reports;
- policy-shaped Bash fence compatibility, canonical fence rewriting and state-machine lint;
- HTTP/WebSocket/URI Process formatting and semantic-diff operations;
- stable `ERROR`, `WARNING` and `INFO` diagnostics;
- HTTP/WebSocket gateway, content negotiation and JSONL event store;
- concrete URI Process validation, contract scopes and idempotent execution;
- `subactor.projects/v1` project registry validation;
- deterministic Plesk publication plans;
- Plesk dry-run/apply/verify executor with exact plan hash and signed grant;
- read-only URI Twin binding in publication plans;
- JavaScript Plesk plan helper and canonical urirun header handling;
- canonical Plesk plan/hash parity between Python and JavaScript;
- offline LLM format/logic benchmark;
- cheapest-capable / lowest-latency / highest-score selection;
- fingerprinted first-request model selection cache;
- situation metrics, assessments and digital-twin routing demo.

## Tested without external infrastructure

Plesk tests use a deterministic fake connector that returns representative
preflight, dry-run, apply and verification receipts. These tests prove local
orchestration behavior and fail-closed guards. They do **not** prove access to a
real Plesk server, DNS provider, vault, signed-grant authority or deployed
`urirun-connector-plesk` instance.

The LLM tests use a deterministic mock adapter. They prove case generation,
format parsing, schema/semantic scoring, cost-aware selection and caching. They
do **not** prove the behavior or current price of a live provider/model.

## Source/build targets not verified in this environment

The repository includes:

- Rust core/CLI scaffold;
- WASM crate;
- PyO3 and N-API crates;
- MQTT v5 bridge;
- protobuf/gRPC service;
- Docker and Compose E2E definitions;
- firmware and Raspberry Pi clients.

These targets require Docker and/or Rust toolchains and are tested by the
provided CI/Compose definitions. A release report must distinguish source
presence from an actually executed build.

## Deliberate limitations

- Semantic diff is structural and does not claim full JSON Schema compatibility analysis.
- `repo-json@1` orders declared properties by schema and dynamic maps lexically; it is a Wellm profile, not a claim of RFC 8785/JCS conformance.
- Source maps identify authored values and their closest parent; generated formatter tokens do not preserve every comment span.
- HCL support is a data-oriented compatibility frontend, not a guarantee of all
  application-specific HashiCorp decoding semantics.
- The TypeScript dialect is a non-executing data subset, not a JavaScript/TS
  runtime or general parser.
- Proto3 support is descriptor/IR oriented; `protoc` remains authoritative for
  complete proto semantics.
- YAML export follows a JSON-compatible profile; comments, anchors and custom
  tags are not a lossless data projection.
- Unknown project gates fail closed.
- Remote Plesk execution is disabled by default in the HTTP service.
- The Plesk planner does not create secrets and does not substitute for the
  connector's own vault, grant and mutation gates.
- URI Twin is read-only and cannot execute a publication.
- Benchmark scores apply only to the configured fixtures, prompts, model route
  and time of execution.
- Unknown LLM cost is not treated as free.

## Release readiness checklist

Before publishing a stable `0.2.0`:

- run Python and Node suites on supported versions;
- run `compose.e2e.yml` with Docker Engine;
- compile/test Rust, WASM, PyO3 and N-API targets;
- run MQTT and gRPC container E2E;
- execute a dry-run against a pinned connector/twin revision;
- validate a controlled Plesk publication with a disposable test domain;
- run a live LiteLLM benchmark with pinned model identifiers and retained cost
  provenance;
- generate and review SBOM, dependency audit and container scan;
- publish versioned JSON Schemas and documentation;
- pin connector, twin and runtime revisions in production configuration.

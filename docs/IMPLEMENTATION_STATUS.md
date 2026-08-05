# Implementation status — 0.2.0rc4

## Working reference implementation

The following components are implemented and covered by local Python/JavaScript
or deterministic contract tests:

- JSON, YAML, TOML, HCL-shaped, typed, restricted TypeScript and TOON data import;
- procedural policy import to structured IR;
- four requested status syntaxes;
- JSON Schema Draft 2020-12 validation;
- exact JSON Schema ⇄ typed schema-module round-trip;
- schema-derived/inferred type annotations and TypeScript/Python code generation;
- generated version registry for dialects, profiles, APIs, schemas and packages;
- generated environment contract, `.env.example`, reference scan and value validation;
- named governance formatting profiles and deterministic governance build/check;
- exact-byte and semantic SHA-256 digests, source maps and semantic diff;
- six-format intent analysis with deterministic todo2code evidence;
- code2llm-style `map.toon.yaml` import to a normalized module map;
- policy Markdown import/lint and compatibility fence rewriting;
- HTTP/WebSocket/URI Process APIs for conversion, versions, env and intent analysis;
- stable `ERROR`, `WARNING` and `INFO` diagnostics;
- content negotiation, Contract AQL, idempotent execution and JSONL event store;
- IoT config and telemetry URI Processes;
- three-layer frontend/backend/firmware Compose example with MQTT v5;
- explicit Docker IPAM and network-collision preflight;
- Plesk project registry, publication plan and fail-closed apply guards;
- read-only URI Twin binding in publication plans;
- JavaScript SDK and Python/JavaScript Plesk plan/hash parity;
- offline LLM format/logic/cost benchmark and first-request model selection;
- situation metrics, assessments and digital-twin routing demo.

## Version-control guarantees

`wellm versions --check` now validates the generated registry rather than only
comparing bytes. It rejects malformed JSON Schemas, missing `$id`, duplicate
identities, unversioned dialect/profile IDs, missing API specs and unhashed API
contracts. Each schema records its contract, version, compatibility policy and
SHA-256.

`wellm env check` validates the single environment contract, scans product-owned
source/Compose/Docker/Make references and validates a local `.env` without
returning secret values.

## Typing boundary

The exact two-way schema path is complete through the typed
`JSONSchema202012` module. Data can also receive type hints from a schema or
structural inference. A general compiler from arbitrary future free-form Wellm
type declarations to every JSON Schema keyword is not claimed in this release;
those annotations are preserved, while the exact reverse path uses the embedded
schema module.

## Tested without external infrastructure

Plesk tests use deterministic fake connector receipts. LLM tests use a mock
adapter. IoT URI/config/telemetry behavior is tested locally in the reference
runtime; the dedicated Compose topology is statically validated and included
for Docker/CI execution.

These tests do not prove access to a live Plesk server, provider credentials,
vault, signed-grant authority, physical IoT device or current LLM behavior.

## Targets requiring external toolchains

The repository includes Rust core/CLI, WASM, PyO3, N-API, MQTT, gRPC, Docker
and firmware build targets. The release report distinguishes source presence
from tests actually executed in the packaging environment.

The supplied Docker build log shows that the previous matrix built its service
images but failed before startup because Docker could not allocate another
network from its predefined address pools. `0.2.0rc4` addresses that specific
failure mode with explicit configurable CIDRs and a preflight. A fresh Docker
run is still required to prove the fix on the affected host.

## Deliberate limitations

- Semantic diff is structural and does not claim full JSON Schema compatibility analysis.
- `repo-json@1` is deterministic but is not a claim of RFC 8785/JCS conformance.
- Source maps identify authored values and their closest parent, not every presentation token.
- HCL support is a static data compatibility frontend, not every application-specific HCL evaluator.
- TypeScript import is a non-executing data subset.
- Proto3 support is descriptor/IR oriented; `protoc` remains authoritative.
- YAML data projection does not preserve comments, anchors or custom tags.
- TOON structural maps normalize compact rows and do not preserve byte-identical presentation.
- Unknown project gates fail closed.
- Remote Plesk execution is disabled by default.
- URI Twin is read-only and cannot execute publication.
- Benchmark scores apply only to their fixtures, model route and execution time.

## Release readiness checklist

Before stable `0.2.0`:

- run `make e2e` on the host that previously exhausted Docker address pools;
- run Python and Node matrices on supported versions;
- compile/test Rust, WASM, PyO3 and N-API targets;
- regenerate and test protobuf stubs with the pinned toolchain;
- execute a dry-run against pinned Plesk connector/twin revisions;
- validate a disposable controlled publication;
- run a live LiteLLM benchmark with pinned model IDs and cost provenance;
- generate/review SBOM, dependency audit and container scan;
- publish versioned schemas/API documents and pin revisions in production.

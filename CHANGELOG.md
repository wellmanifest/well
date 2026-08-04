# Changelog

## [Unreleased]

## [0.2.1] - 2026-08-04

### Docs
- Update CHANGELOG.md
- Update README.md
- Update TEST-REPORT.md
- Update docs/ARCHITECTURE.md
- Update docs/COMPATIBILITY.md
- Update docs/DEPLOYMENT.md
- Update docs/DIALECTS.md
- Update docs/E2E.md
- Update docs/HTTP_API.md
- Update docs/IMPLEMENTATION_STATUS.md
- ... and 8 more files

### Test
- Update tests/test_compatibility.py
- Update tests/test_llmbench.py
- Update tests/test_plesk.py

### Other
- Update .env.example
- Update .gitignore
- Update VERSION
- Update compose.e2e.yml
- Update compose.plesk.example.yml
- Update compose.yml
- Update config/contracts.json
- Update docker/plesk-benchmark-e2e.Dockerfile
- Update examples/any-language/rust/Cargo.toml
- Update examples/benchmark/config.live.example.yaml
- ... and 41 more files


## 0.2.0rc2 — 2026-08-04

- Added exact `subactor.projects/v1` examples for `obslugabiurowa.pl` and
  generated JSON, YAML, typed WellManifest and restricted TypeScript forms.
- Added deterministic Plesk publication planning using concrete URI Processes
  for connector readiness, subscription capacity, DNS authority/propagation,
  TLS probe, file/hash dry-run, guarded apply and publication verification.
- Added a least-privilege `contract:plesk-publication` with exact routes rather
  than a broad Plesk wildcard.
- Added server-side workspace confinement, source-directory allowlisting and
  remote execution disabled by default.
- Added exact connector `plan_hash` and signed apply-grant checks before any
  publication mutation.
- Added read-only `@uri-twin/plesk` binding and documentation separating twin
  facts from connector effects.
- Added `wellm plesk-plan`, `wellm plesk-publish`, HTTP plan/publish endpoints
  and JavaScript/TypeScript plan helpers.
- Added an optional internal LiteLLM benchmark for JSON, YAML, typed
  WellManifest, HCL and restricted TypeScript.
- Added deterministic syntax/schema/semantic scoring, cost/latency/token
  reporting and cheapest-capable first-request selection with fingerprint cache.
- Fixed restricted TypeScript round-trip parsing and preservation of
  single-element object lists in typed output.
- Added Plesk/benchmark schemas, examples, documentation, Docker Compose example
  and local tests.
- Added Python/JavaScript canonical Plesk plan and manifest-hash parity E2E.

## 0.2.0rc1 — 2026-08-04

- Renamed the distribution and primary CLI to `wellm`, while retaining
  `wellmanifest` compatibility entry points.
- Added a restricted, round-trippable TypeScript data dialect.
- Added initial `subactor.projects/v1` and Plesk publication architecture.
- Added initial optional LiteLLM benchmark architecture.

## 0.1.0 — 2026-08-04

- Added the experimental WellManifest protocol/envelope and diagnostic model.
- Added Python reference runtime, CLI, HTTP/WebSocket gateway and JSONL events.
- Added JSON/YAML/TOML, HCL-like, typed, policy and proto3 IR dialects.
- Added the four requested status syntax forms and JSON Schema validation.
- Added capability-scoped URI Process execution and the supplied JS client model.
- Added situation-profile and read-only digital-twin examples.
- Added JavaScript SDK, Rust/WASM/PyO3/N-API scaffolds and firmware clients.
- Added MQTT/gRPC contracts, Docker/Compose E2E and a static landing page.
- Added documentation and examples for SOA, POA, CQRS/ES and LLM integration.

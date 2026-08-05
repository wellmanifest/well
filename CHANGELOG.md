# Changelog

## 0.2.0rc3 — 2026-08-04

- Added `wellm-governance-profile@1` and named profiles for repository JSON,
  wire JSON, YAML JSON-profile, static HCL, typed Wellm, TypeScript data and
  policy Markdown.
- Added deterministic `wellm governance build` and `--check` with schema
  validation, exact-byte drift detection, metadata sidecars and source maps.
- Added independent `artifactSha256` and `semanticSha256` digests with
  Python/JavaScript parity tests.
- Added `wellm fmt`, `wellm profiles`, `wellm semantic-diff`, `wellm roundtrip`
  and policy `import`, `lint` and `fmt` commands.
- Added HTTP, WebSocket and URI Process formatting/semantic-diff operations.
- Policy import now recognizes policy-shaped `bash`/`sh` fences with
  `WM-POLICY-101`, while ordinary shell blocks remain untouched.
- Added state-machine lint that reports the supplied undeclared
  `BLOCKED -> IN_PROGRESS` target instead of guessing a namespace.
- Added current and legacy governance regression fixtures, conditional approval
  evidence tests and generated governance examples.
- Preserved the first normative document header when legend examples contain
  placeholder `DOCUMENT`, `VERSION` or `MODE` declarations.
- Added governance checks to CI, local verification, E2E and the landing page.
- Added JSON Schemas for governance project files, build reports, artifact
  metadata, source maps, conversion reports and semantic diff.
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

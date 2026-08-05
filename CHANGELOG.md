# Changelog

## 0.2.0rc4 — 2026-08-05

- Added a three-layer IoT reference deployment with frontend, backend,
  Mosquitto/bridge and firmware/RPi simulator in `compose.iot.yml`.
- Added IoT config and typed telemetry URI Processes under a least-privilege
  `contract:firmware-thin`.
- Added `make up`, `make down`, `make iot-up`, `make iot-down`, `make e2e-local`,
  `make e2e-docker`, `make iot-e2e` and fail-closed `make e2e` targets.
- Added explicit configurable IPAM subnets and a Docker network preflight to
  avoid exhausted predefined address-pool allocation.
- Added `wellm.env-contract/v1` as the single source for names, defaults, types,
  secret classification and `.env.example` generation across runtime, Make and
  Compose.
- Added `wellm.version-registry/v1` for dialects, formatting profiles, packages,
  OpenAPI/AsyncAPI/proto contracts and every Draft 2020-12 JSON Schema.
- Fixed the version-registry generator so it returns and validates the generated
  object; malformed `null` registries can no longer pass `sync/check`.
- Added schema version and compatibility metadata (`exact-major` or
  `exact-hash`) plus exact contract SHA-256 values.
- Added bidirectional JSON Schema ⇄ typed Wellm schema modules, schema-derived
  data annotations and TypeScript/Python static type generation.
- Added `toon@1` and `toon-map@1`, including import of the supplied code2llm
  `map.toon.yaml` into a normalized 235-module structural map.
- Added six-format intent analysis for JSON, YAML, typed Wellm, HCL, restricted
  TypeScript and TOON, with exact/semantic digests, pairwise diff, schema checks
  and `wellm.todo2code-format-evidence/v1` output.
- Added HTTP, WebSocket, URI Process and JavaScript SDK endpoints for version,
  environment and intent-format discovery/analysis.
- Regenerated OpenAPI and expanded AsyncAPI MQTT/WebSocket contracts for
  request, response and diagnostic envelopes.
- Added `wellm-governance-profile@1`, deterministic repository/wire profiles,
  exact-byte and semantic SHA-256, source maps, governance `build --check`,
  policy linting and semantic round-trip reports.
- Retained fail-closed Plesk planning/publication, URI Twin separation and the
  optional LiteLLM format/logic benchmark.

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

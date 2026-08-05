# End-to-end testing

## Local suites

```bash
make test
make verify
make e2e-local
```

The local suites cover:

1. JSON/YAML/TOML/HCL/typed/TypeScript/TOON parsing and conversion;
2. JSON Schema Draft 2020-12 validation;
3. version registry and environment contract drift;
4. exact JSON Schema ⇄ typed schema-module round-trip;
5. six-format intent comparison and todo2code evidence;
6. governance generation, source maps and policy lint;
7. HTTP, WebSocket and URI Process execution;
8. JavaScript SDK and Raspberry Pi thin client;
9. deterministic Plesk plan parity and fail-closed executor tests;
10. offline LiteLLM benchmark selection.

No Plesk infrastructure is mutated. Publication execution tests use fake
connector receipts.

## Main Docker matrix

```bash
make e2e-docker
```

Equivalent Compose command:

```bash
docker compose --env-file .env -f compose.e2e.yml up \
  --build --abort-on-container-exit --exit-code-from e2e
```

| Service | Environment | Test |
|---|---|---|
| `runtime` | Python/backend | HTTP, WS and process execution |
| `node-e2e` | Node/backend/frontend SDK | conversion and URI client |
| `python-e2e` | Python SDK | capabilities, conversion and execution |
| `firmware-sim` | constrained/RPi simulation | thin remote execution |
| `mqtt` + `mqtt-e2e` | queue/IoT | MQTT v5 correlation and response |
| `grpc` + `grpc-e2e` | SOA/datacenter | protobuf conversion/execution |
| `rust-e2e` | native core | Rust core/CLI tests |
| `plesk-benchmark-e2e` | Python control plane | Plesk planner and offline benchmark |
| `www-e2e` | browser/static | landing endpoint and API availability |

## Three-layer IoT matrix

```bash
make iot-e2e
```

This starts the dedicated frontend, backend, MQTT broker, MQTT bridge and
firmware simulator, then verifies:

- firmware receives remote configuration;
- typed telemetry is accepted under `contract:firmware-thin`;
- an acknowledgement is written to the shared state volume;
- the backend is healthy;
- the frontend can load through its backend proxy.

## Complete test command

```bash
make e2e
```

This is deliberately fail-closed and runs local E2E, the full Docker matrix and
the IoT matrix. Missing Docker is an error, not an implicit host-runtime pass.

## Network preflight

All Compose projects use explicit configurable CIDRs:

```text
WELLMANIFEST_PUBLIC_SUBNET   172.30.240.0/24
WELLMANIFEST_RUNTIME_SUBNET  172.30.241.0/24
WELLMANIFEST_E2E_SUBNET      172.30.242.0/24
WELLMANIFEST_IOT_SUBNET      172.30.243.0/24
```

```bash
make docker-network-doctor
```

The preflight checks a running Docker Engine and reports overlaps before
Compose attempts network creation. Change the relevant `.env` CIDR when the
host already uses one of the defaults.

## Cross-platform CI

The included workflows define:

- Python matrix on Linux, Windows and macOS;
- Node matrix;
- Rust formatting, clippy, tests and WASM build;
- Docker Compose and three-layer IoT E2E on Linux;
- JSON Schema/JSON fixture validation;
- package/archive generation.

## Conformance boundaries

Complete HCL and proto3 compatibility still requires differential testing
against authoritative tool output:

```text
hcl-static parse <-> HashiCorp HCL evaluator/decoder
proto3 IR        <-> protoc FileDescriptorSet
Rust core        <-> Python reference runtime
WASM             <-> Rust native core
```

Until those pass, these remain compatibility frontends rather than claims of
complete language equivalence.

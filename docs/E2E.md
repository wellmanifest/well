# End-to-end testing

## Local suite

```bash
make test
```

It runs Python tests for dialects, policy import, schemas, URI authorization,
runtime/events, situation profiles and ASGI endpoints, then Node's built-in test
runner for the JavaScript SDK.

```bash
make e2e
```

In the packaging environment this completed successfully together with 23
Python tests and 4 Node tests. The script starts the HTTP runtime, then
exercises:

1. health and capability discovery;
2. YAML → JSON conversion;
3. validation against `status.schema.json`;
4. a concrete URI Process under a server contract;
5. event projection;
6. JavaScript SDK tests;
7. Raspberry Pi thin-client simulation.

## Docker matrix

```bash
docker compose -f compose.e2e.yml up \
  --build --abort-on-container-exit --exit-code-from e2e
```

The E2E Compose file contains separate clients/environments:

| Service | Environment | Test |
|---|---|---|
| `runtime` | Python/backend | HTTP, WS and process execution. |
| `node-e2e` | Node/backend/frontend SDK | conversion and URI client. |
| `python-e2e` | Python SDK | schemas and envelope exchange. |
| `firmware-sim` | constrained/RPi simulation | thin remote execution. |
| `mqtt` + `mqtt-e2e` | queue/IoT | MQTT v5 correlation and response. |
| `grpc` + `grpc-e2e` | SOA/datacenter | protobuf conversion/execution. |
| `rust-e2e` | native core | format/CLI tests. |
| `www-e2e` | browser/static | landing endpoint and API availability. |

## Cross-platform CI

The included workflows define:

- Python matrix on Linux, Windows and macOS;
- Node matrix;
- Rust formatting, clippy, tests and WASM build;
- Docker Compose E2E on Linux;
- JSON Schema/JSON fixture validation;
- package/archive generation.

## Conformance fixtures

`tests/fixtures/governance/` contains the supplied governance artifacts. Tests
assert:

- existing `intent.json` validates with its Draft 2020-12 schema;
- existing `manifest.default.json` validates with its schema;
- stable diagnostic codes can be loaded;
- normative Markdown DSL blocks are parsed to policy IR;
- all four status syntaxes normalize to equivalent data.

## Differential tests planned

Full HCL and proto3 compatibility requires comparing the independent parsers
with authoritative tool output. Planned CI fixtures will run:

```text
hcl-lite parse  <-> HashiCorp HCL evaluator/decoder
proto3 IR       <-> protoc FileDescriptorSet
Rust core       <-> Python reference runtime
WASM            <-> Rust native core
```

Until these pass, the implementation labels those dialects as `hcl@2-lite` and
`proto3-ir@1` rather than claiming complete language compatibility.

## Test evidence file

`scripts/package.sh` writes `dist/TEST-REPORT.md` with commands, environment and
results. A release pipeline should attach it with artifact checksums.

# End-to-end testing

## Local suites

```bash
make test
```

This runs the Python tests for dialects, policy import, schemas, URI
authorization, runtime/events, situation profiles, Plesk planning/execution,
LiteLLM benchmark selection and ASGI endpoints, then Node's built-in test runner
for the JavaScript SDK.

```bash
make e2e
```

The local E2E script starts the HTTP runtime and exercises:

1. health and capability discovery;
2. YAML → JSON conversion;
3. validation against `status.schema.json`;
4. a concrete URI Process under a server contract;
5. event projection;
6. JavaScript SDK behavior;
7. Raspberry Pi thin-client simulation;
8. deterministic Plesk plan generation from the supplied project registry;
9. the complete offline LLM benchmark and report generation.

No Plesk infrastructure is mutated. Publication execution tests use fake
connector receipts.

## Docker matrix

```bash
docker compose -f compose.e2e.yml up \
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

The Docker matrix requires Docker Engine and may download pinned base images.
Its result must be reported separately from local tests when Docker is not
available.

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

`examples/plesk/` and `examples/benchmark/` add release-candidate fixtures for:

- exact `subactor.projects/v1` validation;
- workspace source confinement;
- concrete Plesk URI scopes;
- dry-run hash and signed grant enforcement;
- JSON/YAML/typed/TypeScript benchmark round-trip;
- cheapest-capable model and operational-format selection.

## Differential tests planned

Full HCL and proto3 compatibility requires comparing the independent parsers
with authoritative tool output:

```text
hcl-lite parse  <-> HashiCorp HCL evaluator/decoder
proto3 IR       <-> protoc FileDescriptorSet
Rust core       <-> Python reference runtime
WASM            <-> Rust native core
```

Until these pass, the implementation labels those dialects as compatibility
frontends rather than claiming complete language equivalence.

## Python/JavaScript Plesk plan parity

The local E2E suite builds the same `subactor.projects/v1` publication plan in
Python and JavaScript, removes only the non-deterministic timestamp, and requires
identical canonical data and `manifest_hash`:

```bash
PYTHONPATH=src python scripts/e2e-plesk-plan-parity.py
```

This detects frontend/backend normalization drift before a plan reaches the
connector boundary.

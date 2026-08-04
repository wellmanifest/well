# WellManifest


## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.7-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$0.01-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-1.5h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $0.0135 (10 commits)
- 👤 **Human dev:** ~$145 (1.5h @ $100/h, 30min dedup)

Generated on 2026-08-04 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

---



**WellManifest** is an alpha protocol and polyglot runtime for manifests, typed
configuration, procedural policy, URI Process orchestration and format
negotiation. One server can receive JSON, YAML, HCL-like data, typed
WellManifest, policy DSL or proto3 IR and return the representation preferred by
the receiving side.

> Version `0.1.0` is a functional reference implementation and architecture
> package. The Python HTTP/WebSocket runtime, JSON/YAML/TOML conversion, the
> four status syntaxes, JSON Schema validation, URI Process authorization,
> CQRS/ES event log, situation profiles and JavaScript SDK are executable and
> tested. Rust/WASM/PyO3/N-API, MQTT and gRPC are supplied as buildable contracts
> and container targets; they are not yet feature-parity implementations of all
> dialects. The packaged local evidence is 23 Python tests, 4 Node tests and a
> multi-client HTTP/Node/RPi/event-log E2E run.

## Why

A browser may prefer JSON, an operations service YAML, an existing tool HCL, a
strongly typed module WellManifest, a microcontroller a compact protobuf
message, and a governance repository a procedural `RULE/WHEN/DO/FORBID/ASSERT`
policy. WellManifest separates those surface formats from a common envelope,
IR, diagnostics and capability contract.

```text
JSON / YAML / TOML / HCL / typed@1 / policy-sh@1 / proto3
                         │
                         ▼
              WellManifest Document + IR
                         │
       schema validation │ diagnostics │ authorization
                         ▼
              WellManifest Envelope v1
          HTTP │ WebSocket │ MQTT v5 │ gRPC
                         │
                         ▼
 frontend │ backend │ RPi/IoT │ digital twin │ remote runtime
```

## Fast start

### Local reference runtime

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
wellmanifest capabilities
wellmanifest convert examples/dialects/status.yaml --from yaml --to json
wellmanifest validate examples/dialects/status.json --schema schemas/status.schema.json
wellmanifest serve --port 8080
```

### Docker sidecar

```bash
docker compose up --build runtime www
curl http://localhost:8080/healthz
```

Add the runtime to an existing Compose project:

```yaml
services:
  wellmanifest:
    build:
      context: ./vendor/wellmanifest
    environment:
      WELLMANIFEST_DEFAULT_CONTRACT: contract:dev
    ports:
      - "8080:8080"
```

Any language can then use HTTP:

```bash
curl -fsS http://localhost:8080/v1/convert \
  -H 'content-type: application/json' \
  -d '{
    "source":"status:\n  value: SUCCEEDED\n",
    "source_dialect":"yaml",
    "target_dialect":"json",
    "projection":"data"
  }'
```

## Four supported status forms

All four forms normalize to the same data model. The first and fourth remain
HCL-shaped; split and inline typing belong to `typed@1`.

```hcl
status {
  operation = "002-cv-pdf2md"
  value = "SUCCEEDED"
  errors = []
}
```

```wellmanifest
status {
  operation: FolderOperationId
  operation = "002-cv-pdf2md"
  value: OperationState
  value = "SUCCEEDED"
  errors = []
}
```

```wellmanifest
status {
  operation: FolderOperationId = "002-cv-pdf2md"
  value: OperationState = "SUCCEEDED"
  errors: [OperationError] = []
}
```

```hcl
status {
  operation = "002-cv-pdf2md" #folder
  value = "SUCCEEDED" #state
  errors = []
}
```

The comment form is accepted as a legacy hint and emits `WARNING
WM-TYPE-102`; schema or a typed declaration remains the source of truth.
Canonical typed output is `field: Type = value`.

## URI Process

```js
import {UrirunProcessClient} from "@wellmanifest/sdk";

const client = new UrirunProcessClient({
  nodeUrl: "http://localhost:8080",
  contractRef: "contract:dev",
});

const result = await client.execute(
  "youtube://channel/video/query/list",
  {channel: "ours"},
  {allowedUriProcesses: ["youtube://*"], runId: "ticket-002:youtube:1"},
);
```

`youtube://*` is a permission pattern. It is never an executable URI. The
server resolves production authority from a Contract AQL reference, checks the
concrete URI and appends requested/completed/failed events.

## Package and service matrix

| Component | Form | Environment | Status in 0.1.0 | Main use |
|---|---|---|---|---|
| `wellmanifest` | Python package + CLI | backend, RPi | **working/tested** | parsers, conversion, schema validation, local runtime |
| `wellmanifest-server` | FastAPI HTTP/WS service | server, edge | **working/tested** | remote runtime for every language |
| `@wellmanifest/sdk` | dependency-free ES module | browser, Node | **working/tested** | HTTP, WebSocket and URI Process clients |
| `wellmanifest-core` | Rust crate | backend, edge | build scaffold | deterministic JSON/YAML native core |
| `wellmanifest-wasm` | WASM crate | frontend | build scaffold | local browser conversion with remote fallback |
| `wellmanifest-python` | PyO3 crate | Python | build scaffold | native acceleration behind Python API |
| `wellmanifest-node` | N-API crate | Node | build scaffold | native acceleration behind JS API |
| MQTT bridge | MQTT v5 adapter | IoT, queues | source + Compose | request/response topics and correlation data |
| gRPC service | protobuf contract + server | SOA/datacenter | source + Docker generation | unary and bidirectional streaming API |
| firmware thin client | MicroPython/C envelope | MCU, RPi | examples | remote validation/conversion without full parser |
| digital twin router | URI query processes | control plane | **working demo** | read-only portraits, authority/fit/workload routing |
| situation evaluator | DOQL profile adapter | digital twins | **working/tested** | metrics, assessments and decision candidates |
| CQRS/ES store | JSONL event store | backend, edge | **working/tested** | commands, receipts, replayable process events |
| landing page | static HTML/CSS/JS | frontend | included | capabilities and live conversion demo |

## Repository map

```text
src/wellmanifest/       Python reference runtime
packages/js/            browser and Node SDK
crates/                 Rust, CLI, WASM, PyO3 and N-API crates
proto/                  gRPC/protobuf contract
schemas/                JSON Schema 2020-12 contracts
examples/               HCL, typed DSL, policy, SOA, POA, IoT, twins, LLM
www/                    project landing page
Dockerfile              HTTP/WebSocket runtime image
compose.yml             runtime, MQTT, gRPC, site and firmware simulator
docs/                   architecture and operational documentation
tests/                  local and source-compatibility tests
```

## Commands

```bash
make test              # Python + Node tests
make serve             # HTTP/WebSocket gateway
make proto             # generate Python gRPC stubs
make e2e               # local multi-client E2E
make package           # source ZIP and tar.gz
```

## Security boundary

WellManifest is not a generic remote shell. The reference service:

- accepts only concrete URI Processes;
- treats wildcards as contract scopes only;
- executes registered adapters, never arbitrary source code;
- supports idempotent run IDs and append-only events;
- keeps digital twins read-only and unable to expand authority;
- plans HTTP and GPIO operations without performing mutations by default;
- returns stable `ERROR`, `WARNING` and `INFO` diagnostics.

See [docs/SECURITY.md](docs/SECURITY.md) and
[docs/URI_PROCESS.md](docs/URI_PROCESS.md).

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Protocol and content negotiation](docs/PROTOCOL.md)
- [Dialects and four syntaxes](docs/DIALECTS.md)
- [Transport contracts](docs/TRANSPORTS.md)
- [Generated HTTP/OpenAPI API](docs/HTTP_API.md)
- [Plugin and external-language adapter model](docs/PLUGINS.md)
- [URI Process and Contract AQL](docs/URI_PROCESS.md)
- [SOA, POA, CQRS and Event Sourcing](docs/SOA_POA_CQRS_ES.md)
- [Digital twins and situation profiles](docs/DIGITAL_TWINS.md)
- [Firmware and Raspberry Pi](docs/FIRMWARE.md)
- [LLM integration](docs/LLM.md)
- [Docker and deployment](docs/DEPLOYMENT.md)
- [E2E testing](docs/E2E.md)
- [Compatibility matrix](docs/COMPATIBILITY.md)
- [Implementation status and limitations](docs/IMPLEMENTATION_STATUS.md)
- [Roadmap](docs/ROADMAP.md)

## Provenance of the governance examples

The PyPI distribution name is `wellmanifest`. The external `well` package is
not a hard dependency: `wellmanifest.integrations.well` detects it only when a
compatible installation is present, without inventing or binding to an
undocumented API.

The fixtures under `tests/fixtures/governance/` are copies of the supplied
`wellmanifest/new-project` manifest, intent, schemas, diagnostics, stack
profiles and `CONTRIBUTING.md`. Tests prove that the current JSON instances
remain valid and the normative DSL blocks can be imported into policy IR.

## License

Licensed under Apache-2.0.

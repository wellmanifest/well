# wellm — WellManifest protocol and runtime

**wellm** is a polyglot manifest protocol, typed DSL runtime and URI Process
control layer. It normalizes JSON, YAML, TOML, HCL-shaped data, strongly typed
WellManifest, procedural policy, restricted TypeScript data modules and proto3
IR into one document/envelope model with schema validation and structured
`ERROR`, `WARNING` and `INFO` diagnostics.

Release candidate `0.2.0rc3` adds `wellm-governance-profile@1`: named
formatting profiles, deterministic repository JSON, semantic and exact-byte
hashes, source maps, governance `build --check`, policy Markdown linting,
semantic diff and round-trip reports. It retains the fail-closed Plesk
publication workflow and optional LiteLLM benchmark introduced in the previous
candidate.

> This repository is a reference implementation and release candidate, not a
> hosted production control plane. The Python runtime, CLI, HTTP/WebSocket API,
> JSON/YAML/TOML conversion, four status forms, project/Plesk planner, offline
> LLM benchmark and JavaScript SDK are executable. Rust/WASM/PyO3/N-API remain
> compatibility scaffolds; MQTT/gRPC and Docker E2E have container definitions
> but require their corresponding toolchains/runtime.

## Architecture

```text
JSON / YAML / TOML / HCL / typed@1 / TypeScript / policy-sh@1 / proto3
                                  │
                                  ▼
                    WellManifest Document + Core IR
                                  │
              schema · types · diagnostics · policy
                                  ▼
                       WellManifest Envelope v1
          HTTP · WebSocket · MQTT v5 · protobuf/gRPC · events
                                  │
                                  ▼
      browser · backend · RPi/IoT · digital twin · remote runtime
                                  │
                                  ▼
       concrete URI Process · Contract AQL · adapter · receipt
```

Different parties may send and receive their preferred representation. The
runtime negotiates the external format while preserving a canonical data or IR
projection internally.

## Install

From a local checkout:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
wellm --version
wellm capabilities
```

Optional transports and LLM benchmark:

```bash
python -m pip install -e '.[all]'
# or only LiteLLM support
python -m pip install -e '.[benchmark]'
```

The former `wellmanifest` commands and Python namespace remain compatibility
aliases. New code should use the `wellm` distribution and CLI.
 The original
`from well import hello, greet` API from `wellm` 0.1.x is retained; see
[docs/MIGRATION_0.1_TO_0.2.md](docs/MIGRATION_0.1_TO_0.2.md).

## Fast start

```bash
wellm convert examples/dialects/status.yaml --from yaml --to json
wellm validate examples/dialects/status.json --schema schemas/status.schema.json
wellm serve --port 8080
```

```bash
curl -fsS http://localhost:8080/healthz
curl -fsS http://localhost:8080/v1/capabilities
```

Docker sidecar:

```bash
docker compose up --build runtime www
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

## Four status forms

All four requested forms normalize to the same data model.

Strict HCL-shaped data:

```hcl
status {
  operation = "002-cv-pdf2md"
  value = "SUCCEEDED"
  errors = []
}
```

Split type declaration and value, accepted for compatibility:

```wellmanifest
status {
  operation: FolderOperationId
  operation = "002-cv-pdf2md"
  value: OperationState
  value = "SUCCEEDED"
  errors = []
}
```

Canonical strongly typed form:

```wellmanifest
status {
  operation: FolderOperationId = "002-cv-pdf2md"
  value: OperationState = "SUCCEEDED"
  errors: [OperationError] = []
}
```

Legacy comment hint:

```hcl
status {
  operation = "002-cv-pdf2md" #folder
  value = "SUCCEEDED" #state
  errors = []
}
```

The comment form emits `WM-TYPE-102`. A comment is never the normative source of
a type; the typed declaration or schema is.

## Governance authoring and deterministic JSON

Wellm can now be the authoring layer while existing scripts continue consuming
JSON and JSON Schema:

```bash
wellm governance build examples/governance/wellm.project.yaml
wellm governance build examples/governance/wellm.project.yaml --check
```

The example generates manifest, ticket intent, diagnostics, stack profiles,
metadata sidecars, source maps and policy IR. The generated JSON is validated
against the supplied Draft 2020-12 schemas.

Useful commands:

```bash
wellm profiles
wellm fmt examples/governance/manifest.wm \
  --profile repo-json@1 \
  --schema examples/governance/fixtures/manifest.schema.json
wellm policy lint examples/governance/fixtures/CONTRIBUTING.md
wellm semantic-diff \
  tests/fixtures/governance-current/manifest.default.json \
  tests/fixtures/governance-legacy/manifest.default.json
wellm roundtrip examples/governance/generated/manifest.default.json \
  --via yaml,typescript,json \
  --schema examples/governance/fixtures/manifest.schema.json
```

`artifactSha256` tracks exact bytes used by lock/adoption tooling;
`semanticSha256` tracks normalized meaning. Metadata is stored in sidecars, so
closed JSON Schemas are not modified.

Full guide: [docs/GOVERNANCE_FORMATTING.md](docs/GOVERNANCE_FORMATTING.md).

## Plesk publication from `subactor.projects/v1`

The exact project registry in
[`examples/plesk/projects.json`](examples/plesk/projects.json) can be validated
and converted into a deterministic publication plan:

```bash
wellm validate examples/plesk/projects.json \
  --schema schemas/projects.schema.json

wellm plesk-plan examples/plesk/projects.json \
  --project obslugabiurowa-pl \
  --source-ref workspace:obslugabiurowa-pl=examples/plesk/site/www \
  --workspace-root . \
  --to yaml
```

The plan separates read-only twin facts from connector effects and contains:

```text
connector readiness
→ read-only subscription and docroot twin facts
→ subscription capabilities
→ DNS authority and propagation
→ non-mutating TLS probe
→ non-mutating file/hash dry-run
→ signed exact-hash apply
→ DNS/TLS/HTTPS/content verification
```

Remote dry-run:

```bash
export URIRUN_NODE_URL=http://urirun-bridge:8080
export URIRUN_TOKEN='from-secret-store'

wellm plesk-publish examples/plesk/projects.extended.yaml \
  --project obslugabiurowa-pl \
  --source-ref workspace:obslugabiurowa-pl=examples/plesk/site/www \
  --workspace-root . \
  --node-url "$URIRUN_NODE_URL"
```

Apply is blocked unless the preflight is green and the operator supplies the
exact connector `plan_hash` plus a signed single-use grant:

```bash
export URIRUN_APPLY_GRANT='signed-single-use-grant'

wellm plesk-publish examples/plesk/projects.extended.yaml \
  --project obslugabiurowa-pl \
  --source-ref workspace:obslugabiurowa-pl=examples/plesk/site/www \
  --workspace-root . \
  --node-url "$URIRUN_NODE_URL" \
  --apply --plan-hash "$CONNECTOR_PLAN_HASH"
```

No credential belongs in the registry. Only opaque vault references are
accepted. Production autonomous execution should route through the trusted
Control/Bridge boundary and server-side Contract AQL, not expose a raw node to a
browser or device.

Full guide: [docs/PLESK_PUBLICATION.md](docs/PLESK_PUBLICATION.md).

## LiteLLM format and logic benchmark

Run the reproducible offline benchmark:

```bash
wellm benchmark-llm examples/benchmark/config.yaml \
  --mock \
  --output-dir .wellm/benchmark
```

It generates JSON, YAML, typed WellManifest and restricted TypeScript tasks and
checks every completion using:

| Check | Weight |
|---|---:|
| target parser | 25% |
| JSON Schema 2020-12 | 25% |
| exact normalized semantics | 50% |

The default cases measure project round-trip, concrete URI/wildcard permission
logic and fail-closed publication gates. The selector picks the cheapest model
that passes all configured thresholds; a cheaper model that cannot handle a
required format is rejected.

A live benchmark uses LiteLLM:

```bash
cp examples/benchmark/config.live.example.yaml .wellm/benchmark.live.yaml
# edit model identifiers and set provider credentials in environment variables
wellm benchmark-llm .wellm/benchmark.live.yaml \
  --output-dir .wellm/benchmark/live
```

`FirstRequestModelSelector` benchmarks fixed synthetic fixtures and caches the
winner before forwarding the actual application request. The real request is
not broadcast to every candidate.

Full guide: [docs/LLM_BENCHMARK.md](docs/LLM_BENCHMARK.md).

## URI Process client

```js
import {UrirunProcessClient} from "@wellmanifest/wellm-sdk";

const client = new UrirunProcessClient({
  nodeUrl: "http://localhost:8080",
  token: process.env.URIRUN_TOKEN,
  contractRef: "contract:dev",
});

const result = await client.execute(
  "youtube://channel/video/query/list",
  {channel: "ours"},
  {allowedUriProcesses: ["youtube://*"], runId: "ticket-002:youtube:1"},
);
```

`youtube://*` is a permission pattern and never an executable address. The
client rejects a wildcard URI before network contact; the trusted server must
independently resolve authority from the active contract.

## Package, service and runtime matrix

| Layer | Package/service | Frontend | Backend | RPi/IoT | Digital twin | Main role | Maturity in `0.2.0rc3` |
|---|---|---:|---:|---:|---:|---|---|
| protocol | `wellmanifest.protocol/v1` | yes | yes | yes | yes | envelope, negotiation, diagnostics | specified + schemas |
| Python | `wellm` / `wellmanifest` alias | remote client | local/service | RPi | control | parsers, validation, planner, benchmark | **working/tested** |
| CLI | `wellm` | dev tooling | ops | Linux RPi | admin | convert, validate, format, governance, diff, Plesk, benchmark | **working/tested** |
| HTTP/WS | `wellm-server` | fetch/WS | any language | thin client | queries | shared remote runtime | **working/tested** |
| JavaScript | `@wellmanifest/wellm-sdk` | local client | Node | gateway | queries | URI client and Plesk plan helper | **working/tested** |
| Plesk planner | `wellm.plesk` | call service | local/service | remote only | consumes facts | plan, dry-run, guarded apply, verify | **working/tested with fake connector** |
| LLM benchmark | `wellm.llmbench` | reports | Python | remote | planning | format/logic/cost selection | **offline tested; live optional** |
| Rust core | `wellmanifest-core` | via WASM | native | ARM Linux | projections | native conversion core | scaffold |
| WASM | `wellmanifest-wasm` | local | edge | limited | projections | browser conversion | scaffold |
| PyO3/N-API | native bindings | Node | Python/Node | Linux RPi | control | acceleration | scaffold |
| MQTT bridge | `wellm-mqtt` | gateway | queue | devices | events | request/response topics | source + Compose |
| gRPC | `wellm-grpc` | gateway | SOA | edge | streams | protobuf API | source + Compose |
| firmware thin client | MicroPython/C examples | — | remote | MCU/RPi | — | small envelope and remote runtime | examples |
| digital twin router | situation/twin URI processes | read | service | telemetry | native | read-only portrait and routing | working demo |
| CQRS/ES | JSONL event store | read | local | edge buffer | projection | command/receipt replay | working/tested |

More detail: [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## Repository map

```text
src/wellmanifest/          implementation and compatibility namespace
src/wellm/                 primary Python namespace aliases
src/wellmanifest/plesk.py  project registry, planner and guarded executor
src/wellmanifest/llmbench/ deterministic benchmark and LiteLLM adapter
packages/js/               browser/Node SDK and TypeScript declarations
crates/                    Rust, CLI, WASM, PyO3 and N-API scaffolds
proto/                     protobuf/gRPC contract
schemas/                   JSON Schema 2020-12 and OpenAPI/AsyncAPI
examples/plesk/            real project registry and publication examples
examples/benchmark/        offline/live model selection examples
www/                       landing page
compose*.yml               runtime and E2E environments
docs/                      protocol, deployment and integration guides
tests/                     parser, schema, governance, Plesk and benchmark tests
```

## Development and verification

```bash
make test
python -m pytest -q
(cd packages/js && npm test)
python -m compileall -q src
```

Docker E2E:

```bash
docker compose -f compose.e2e.yml up \
  --build --abort-on-container-exit --exit-code-from e2e
```

The Plesk connector live path is intentionally not exercised by default. Local
and CI tests use deterministic fake receipts and do not mutate infrastructure.

## Security boundary

wellm is not a generic remote shell. The reference runtime:

- accepts only concrete URI Processes;
- treats wildcards as contract scopes only;
- invokes registered adapters, never arbitrary model-generated code;
- keeps URI Twin data read-only and unable to expand authority;
- resolves publication sources under an allowlisted workspace root;
- defaults Plesk execution to dry-run;
- requires a connector plan hash and signed grant before apply;
- keeps secrets outside manifests, benchmark reports and source control;
- records stable structured diagnostics and receipts;
- validates LLM output independently of the selected provider.

See [docs/SECURITY.md](docs/SECURITY.md),
[docs/URI_PROCESS.md](docs/URI_PROCESS.md) and
[docs/PLESK_PUBLICATION.md](docs/PLESK_PUBLICATION.md).

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Protocol and negotiation](docs/PROTOCOL.md)
- [Dialects](docs/DIALECTS.md)
- [Governance formatting](docs/GOVERNANCE_FORMATTING.md)
- [Plesk publication](docs/PLESK_PUBLICATION.md)
- [LLM benchmark](docs/LLM_BENCHMARK.md)
- [HTTP API](docs/HTTP_API.md)
- [Transports](docs/TRANSPORTS.md)
- [URI Process](docs/URI_PROCESS.md)
- [SOA, POA, CQRS and Event Sourcing](docs/SOA_POA_CQRS_ES.md)
- [Digital twins](docs/DIGITAL_TWINS.md)
- [Firmware and Raspberry Pi](docs/FIRMWARE.md)
- [Docker deployment](docs/DEPLOYMENT.md)
- [E2E testing](docs/E2E.md)
- [Compatibility matrix](docs/COMPATIBILITY.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md)
- [Roadmap](docs/ROADMAP.md)

## Governance compatibility

The supplied `wellmanifest/new-project` manifest, intent, schemas, diagnostics,
stack profiles, approval evidence schema and procedural `CONTRIBUTING.md` are
retained as current and legacy regression fixtures. JSON Schema remains the
deterministic data contract. Wellm can generate instance JSON without adding
metadata fields to closed records, and policy imports remain independent of any
LLM provider.

The external PyPI project named `well` is not a hard dependency. The integration
adapter only detects it when a compatible installation is present; wellm does
not invent or bind to an undocumented API.

## License

Apache-2.0.

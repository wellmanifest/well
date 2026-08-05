# Compatibility and usage matrix

## Packages, services and runtimes

| Layer | Package/service | Local | Remote | Browser | Backend | RPi/IoT | Digital twin | Maturity `0.2.0rc4` |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Protocol | `wellmanifest.protocol/v1` | yes | yes | yes | yes | yes | yes | specified + schemas |
| Python distribution | `wellm` | yes | client/server | no | yes | CPython RPi | control | tested reference |
| Compatibility namespace | `wellmanifest` | yes | client/server | no | yes | CPython RPi | control | retained |
| CLI | `wellm` | yes | calls service/node | dev tools | ops | Linux RPi | admin | tested |
| HTTP/WS gateway | `wellm-server` | sidecar | yes | fetch/WS | any language | thin client | query | tested |
| JavaScript SDK | `@wellmanifest/wellm-sdk` | client/helpers | yes | yes | Node | gateway | query | tested |
| Plesk publication | `wellm.plesk` | planner/executor | bridge/node | plan only | yes | remote only | consumes read-only facts | fake-connector tested |
| URI client | `wellm.urirun` | yes | canonical `/run` | JS equivalent | yes | thin client | bridge | tested |
| LLM benchmark | `wellm.llmbench` | Python | provider APIs | report UI | yes | remote | planner | offline tested, live optional |
| Rust | `wellmanifest-core` | yes | via service | through WASM | yes | Linux ARM | projection | scaffold |
| WASM | `wellmanifest-wasm` | yes | fallback | yes | edge | limited | projection | scaffold |
| PyO3 | `wellmanifest-python` | yes | no | no | yes | Linux RPi | control | scaffold |
| N-API | `wellmanifest-node` | yes | no | yes/Node | Node | gateway | control | scaffold |
| version registry | `wellm.version-registry/v1` | yes | HTTP/URI | consume | enforce | consume | contract discovery | tested |
| environment contract | `wellm.env-contract/v1` | yes | HTTP/URI | consume | enforce | consume | configuration names | tested |
| intent-format analysis | `wellm.intent-format-analysis/v1` | yes | HTTP/URI | report | service | evidence | intent drift | tested |
| MQTT | `wellm-mqtt` | broker/bridge | yes | gateway | queue | device | events | source + local contracts; Compose target |
| gRPC | `wellm-grpc` | generated | yes | gateway | SOA | edge | streams | source + Compose/CI target |
| firmware client | MQTT/RPi simulator | yes | server | no | no | yes | telemetry | source + local runtime tests; Compose target |
| situation evaluator | Python adapter | yes | service | query | yes | telemetry | native | tested |
| twin router | URI query process | yes | service | query | yes | telemetry | native | working demo |
| CQRS/ES | JSONL event store | yes | service | read | yes | edge buffer | projection | tested |
| Landing page | `www/` | static | CDN/sidecar | yes | no | no | dashboard | included |

`yes` means the layer is designed for that environment. It does not imply every
native implementation has feature parity. The Python runtime is the semantic
reference for this release candidate.

## Plesk publication variants

| Variant | Caller | Execution endpoint | Twin use | Mutation | Recommended use |
|---|---|---|---|---:|---|
| local plan | `wellm plesk-plan` | none | pinned read-only metadata | no | CI, review, GitOps artifact generation |
| trusted dry-run | `wellm plesk-publish` | trusted bridge/node `/run` | readiness context | no | integration and operator preflight |
| guarded apply | `wellm plesk-publish --apply` | trusted bridge/node | readiness context | yes, exact hash + signed grant | controlled release |
| HTTP plan service | `/v1/plesk/plan` | wellm server | read-only | no | browser/backend clients |
| HTTP execution service | `/v1/plesk/publish` | wellm server → bridge/node | read-only | disabled by default | private control plane only |
| Subactor autonomous path | Control → Bridge → connector | isolated connector node | actor/environment portrait | gated | production autonomy |

## Format and projection compatibility

| Source / target | Data import | Data export | Full IR | Round-trip expectation |
|---|---:|---:|---:|---|
| JSON RFC 8259 | yes | yes | yes | lossless for JSON values |
| YAML 1.2 JSON profile | yes | yes | yes | normalized; comments/anchors not preserved |
| TOML | yes | yes | data only | lossy for unsupported TOML presentation details |
| HCL-shaped data | yes | yes | parser IR | normalized, not byte-identical HCL |
| typed WellManifest | yes | yes | yes | canonical formatter output; schema hints preserved |
| TOON/code2llm map | yes | normalized map/YAML | data/IR | compact structural map; presentation normalized |
| policy-sh | policy IR | generated IR | yes | full semantics in IR, not plain data |
| safe TypeScript data module | yes | yes | data/IR | restricted subset only; no code execution |
| proto3 | descriptor-oriented | source/IR scaffold | yes | canonical format remains `.proto`/descriptor set |

## LLM benchmark matrix

| Format | Parse check | Schema check | Semantic check | Default benchmark |
|---|---:|---:|---:|---:|
| JSON | yes | yes | exact normalized equality | yes |
| YAML | yes | yes | exact normalized equality | yes |
| typed WellManifest | yes | yes | exact normalized equality | yes |
| TypeScript data module | yes | yes | exact normalized equality | yes |
| HCL | yes | yes | exact normalized equality | opt-in |

Selection policies:

| Policy | Primary criterion | Tie-breakers |
|---|---|---|
| `lowest_cost` | lowest known measured total cost among capable models | score, latency |
| `highest_score` | highest deterministic score | known cost, latency |
| `lowest_latency` | lowest measured average latency | score, known cost |

A model is not capable unless it passes the configured total threshold and the
minimum score for every required format.

## Environment matrix

| Environment | Preferred deployment | Local capabilities | Remote fallback |
|---|---|---|---|
| browser | JS SDK + optional WASM | JSON/YAML/basic typed conversion | HTTP/WS wellm service |
| Node backend | JS SDK or N-API later | plan helpers and URI client | HTTP/gRPC service |
| Python backend | `wellm` | full reference runtime, Plesk planner, benchmark | remote gateway/provider |
| Rust backend | native crate when completed | JSON/YAML core scaffold | Python/server reference |
| Raspberry Pi Linux | Python package or ARM container | thin/local operations | server/edge gateway |
| MicroPython/MCU | small envelope client | serialization and transport | all parsing/validation/execution |
| Kubernetes/datacenter | sidecar/service | horizontally deployable gateway | connector-specific control planes |
| digital twin | read-only service/profile | facts and routing projection | effect adapter remains separate |

## Security compatibility

Every environment must preserve these invariants:

1. wildcard patterns exist only in authority scopes;
2. execution uses a concrete URI without `*`;
3. manifests contain no credentials;
4. adapters are explicitly registered;
5. Plesk apply uses the exact dry-run hash and signed grant;
6. LLM output is untrusted until parsed, schema-validated and policy-checked;
7. a runtime profile never expands Contract AQL authority;
8. receipts and diagnostics remain stable across local and remote bindings.

## Governance-formatting matrix

| Capability | Python CLI/API | HTTP/WS | JavaScript SDK | Firmware/thin client |
|---|---:|---:|---:|---:|
| list profiles | yes | yes | remote | remote |
| `repo-json@1` formatting | yes | yes | canonical helper + remote | remote |
| semantic SHA-256 | yes | service | yes | service |
| source maps | yes | returned through IR/build artifacts | consume | consume |
| governance build/check | yes | deployment-side | call service/CI | no |
| policy Markdown import/lint | yes | runtime/IR | consume IR | no |
| semantic diff | yes | yes | remote | remote |
| round-trip report | yes | via conversion API | client orchestration | remote |

## Contract-control matrix

| Surface | Source of truth | Drift command | Runtime discovery |
|---|---|---|---|
| dialects and formatting profiles | parser/profile registries | `make versions-check` | `GET /v1/versions` |
| HTTP, WebSocket, MQTT, gRPC | OpenAPI, AsyncAPI, proto | `make versions-check` | `GET /v1/versions` |
| JSON Schema 2020-12 | `schemas/*.schema.json` | `make versions-check` | registry path/id/version/hash |
| environment variables | `config/env-contract.json` | `make env-check` | `GET /v1/env-contract` without values |
| Docker networks/ports/images | environment contract + Compose | `make compose-check` and network preflight | `.env`/Compose config |
| typed schema bridge | JSON Schema or typed schema module | `make schema-demo`, `make verify` | CLI/API conversion metadata |

## Three-layer IoT matrix

| Layer | Artifact | Local protocol | Remote runtime role |
|---|---|---|---|
| frontend | `examples/iot-three-layer/frontend/` | HTTP to backend | event/config display |
| backend | `wellm-server` | HTTP/WS + JSONL events | schema/URI execution and discovery |
| firmware | `examples/iot-three-layer/firmware/device.py` | MQTT v5 envelope | thin config/telemetry client |
| transport | Mosquitto + `wellm-mqtt` | MQTT response topic/correlation data | contract enforcement bridge |

The dedicated `compose.iot.yml` and `make iot-up/iot-down/iot-e2e` targets use
one explicit subnet and the same generated `.env` contract as the main stack.

# Compatibility and usage matrix

## Packages and runtimes

| Layer | Package/service | Local | Remote | Browser | Backend | RPi/IoT | Digital twin | Maturity 0.1.0 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Protocol | `wellmanifest.protocol/v1` | yes | yes | yes | yes | yes | yes | specified + schemas |
| Python | `wellmanifest` | yes | client/server | no | yes | RPi | yes | tested reference |
| JavaScript | `@wellmanifest/sdk` | client | yes | yes | Node | JS gateway | yes | tested client |
| Rust | `wellmanifest-core` | yes | via service | WASM | yes | Linux RPi | yes | build scaffold |
| WASM | `wellmanifest-wasm` | yes | fallback | yes | edge | limited | projections | build scaffold |
| PyO3 | `wellmanifest-python` | yes | no | no | yes | RPi Linux | yes | build scaffold |
| N-API | `wellmanifest-node` | yes | no | no | Node | edge | yes | build scaffold |
| CLI | Python/Rust CLI | yes | calls server | dev tools | ops | RPi Linux | admin | Python tested |
| HTTP | FastAPI gateway | n/a | yes | fetch | any language | thin client | yes | tested |
| WebSocket | `/v1/ws` | n/a | yes | live editor | streaming | gateway | live status | implemented |
| MQTT | bridge | gateway | broker | via broker lib | yes | yes | telemetry | source/Compose |
| gRPC | RuntimeService | n/a | yes | grpc-web via proxy | yes | capable edge | streaming | contract/source |
| CQRS/ES | JSONL store | yes | API | query | yes | gateway | receipts | tested demo |
| URI Process | process router | yes | yes | client | yes | delegated | routing | tested demo |
| Situation profile | evaluator | yes | URI/API | result only | yes | snapshot sender | primary | tested subset |
| LLM planner | adapter contract | provider | service | client | yes | remote only | proposals | safe mock |

## Dialect conversion

Legend: **L** lossless/semantic, **N** normalized, **I** IR required, **P**
partial subset, `—` unsupported in 0.1.0.

| From / to | JSON | YAML | TOML | HCL | typed | policy | proto3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| JSON | L | N | N | N | N | — | I/P |
| YAML JSON profile | N | L | N | N | N | — | I/P |
| TOML | N | N | L | N | N | — | I/P |
| HCL data subset | N | N | N | N | N | — | — |
| typed data | N | N | N | N | N | I | I |
| policy DSL | I | I | — | — | I | N | — |
| proto3 | I/P | I/P | — | — | I | — | N/descriptor |

## Environment selection

| Environment declaration | Preferred runtime | Fallback | Typical transport |
|---|---|---|---|
| `frontend` | WASM/JS SDK | remote gateway | HTTP/WS |
| `backend` | Rust/Python in-process | remote gateway | native/HTTP/gRPC |
| `firmware` | thin client | edge gateway | MQTT/HTTP/protobuf |
| `rpi` | native Rust or Python | remote gateway | native/MQTT/HTTP |
| `digital-twin` | server projection/router | remote service | HTTP/gRPC/events |
| `datacenter` | worker pools | regional gateway | gRPC/queues |

## Digital-twin artifacts

| Artifact | Mutable? | Contains authority? | Purpose |
|---|---:|---:|---|
| portrait/profile | no | references current contract only | routing fit and workload snapshot |
| Contract AQL | controlled | yes | exact capability boundary |
| situation snapshot | append/versioned | no | facts used by metrics |
| situation profile | versioned | no mutation authority | deterministic assessment logic |
| routing decision | event/receipt | no new authority | reproducible candidate selection |
| execution receipt | immutable | evidence only | prove result/EQL handoff |

## Support policy

Version 0.1.0 is experimental. JSON/YAML, JSON Schema, Python runtime and JS SDK
are the conformance baseline. Full HCL, proto, native bindings and distributed
stores require further compatibility and operational testing before stable
claims.

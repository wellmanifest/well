# Deployment

## Development stack

```bash
cp .env.example .env
docker compose up --build
```

Services:

| Service | Port | Role |
|---|---:|---|
| `runtime` | 8080 | Python HTTP/WebSocket reference runtime and landing API. |
| `grpc` | 50051 | protobuf/gRPC service generated from the shared contract. |
| `mqtt` | 1883 | development MQTT broker. |
| `mqtt-bridge` | internal | MQTT v5 envelope bridge to the same runtime. |
| `www` | 8088 | standalone static landing page; optional because runtime also serves it. |
| `firmware-sim` | internal | thin-client/RPi simulation. |

The development broker allows anonymous local clients; do not copy that setting
to production.

## Sidecar in an existing Compose project

```yaml
services:
  application:
    image: example/application:1.0
    environment:
      WELLMANIFEST_URL: http://wellm:8080
    depends_on:
      wellm:
        condition: service_healthy

  wellm:
    build:
      context: ./vendor/wellm
    environment:
      WELLMANIFEST_DEFAULT_CONTRACT: contract:dev
      WELLMANIFEST_EVENT_STORE: /data/events.jsonl
    volumes:
      - wellm-data:/data
      - ./contracts.json:/app/config/contracts.json:ro
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"]
      interval: 5s
      timeout: 2s
      retries: 20

volumes:
  wellm-data: {}
```


## Plesk publication sidecar

Use [`compose.plesk.example.yml`](../compose.plesk.example.yml) as a minimal
starting point:

```bash
docker compose -f compose.plesk.example.yml up --build wellm
```

The source workspace is mounted read-only. Keep connector/vault secrets out of
Compose and attach the trusted Subactor Bridge or urirun node over a private
network. `WELLMANIFEST_ENABLE_PLESK_EXECUTION` remains `0` until the Contract
AQL, vault lease, exact plan hash and signed apply-grant boundary are configured.

## LLM benchmark service profile

The offline benchmark requires no provider key and is suitable for CI:

```bash
docker compose -f compose.e2e.yml run --rm plesk-benchmark-e2e
```

For a live LiteLLM benchmark, build/install the `benchmark` extra and inject
provider credentials from the deployment secret manager. Do not place API keys
in the benchmark YAML, image layer, Compose file or result artifact.

## Copy a native runtime from a builder image

After publishing images, an application image can copy the Rust CLI:

```dockerfile
FROM wellmanifest/wellm-runtime-rust:0.2.0rc2 AS wellm
FROM gcr.io/distroless/cc-debian12
COPY --from=wellm /usr/local/bin/wellmanifest-native /usr/local/bin/wellm-native
ENTRYPOINT ["/usr/local/bin/wellm-native"]
```

The repository provides `docker/runtime-rust.Dockerfile` to build this target.
Until an image is published, use the local build context and do not assume the
example tag exists in a registry.

## Frontend

Two modes are supported:

1. dependency-free JS SDK calls the remote runtime;
2. `wellmanifest-wasm` is the planned native browser path and handles lightweight JSON/YAML operations in the browser
   and falls back to the remote server for policy, proto, schemas or privileged
   URI Processes.

Serve the `www/` folder directly or through the runtime. Set the API base URL in
`www/app.js`/deployment configuration.

## Backend

Python applications can import `WellManifestRuntime` in-process or use
`WellManifestClient`. Other languages use HTTP, WS, MQTT or generated gRPC
clients. This avoids requiring a native binding for every language.

## Raspberry Pi and edge gateway

An RPi can run the Python image, build the native Rust CLI for `linux/arm64`, or
act as a thin client. Use Buildx for multi-architecture images:

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f Dockerfile \
  -t registry.example/wellmanifest/wellm:0.2.0rc2 \
  --push .
```

A 32-bit/MCU target should normally use the thin protocol client rather than a
full parser container.

## Kubernetes/large installations

Split responsibilities:

```text
ingress
  |
  +-- stateless protocol gateways (HTTP/WS/gRPC)
  +-- MQTT/queue ingress adapters
  +-- contract/schema registry cache
  +-- process workers by connector/runtime class
  +-- durable event/idempotency store
  +-- digital-twin/situation projections
```

Scale conversion workers independently from connector workers. Use tenant-aware
queues, network policies and per-contract rate limits. Pin runtime and schema
revisions in envelopes/receipts.

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `WELLMANIFEST_HOST` | `0.0.0.0` | HTTP bind host. |
| `WELLMANIFEST_PORT` | `8080` | HTTP bind port. |
| `WELLMANIFEST_TOKEN` | empty | Optional development bearer/token guard. |
| `WELLMANIFEST_CONTRACTS` | `config/contracts.json` | Server-side contracts file. |
| `WELLMANIFEST_DEFAULT_CONTRACT` | `contract:dev` | Development default only. |
| `WELLMANIFEST_EVENT_STORE` | `/data/events.jsonl` | Event log path. |
| `WELLMANIFEST_WORKSPACE_ROOT` | empty | Trusted root for `workspace:*` publication sources. |
| `WELLMANIFEST_ENABLE_PLESK_EXECUTION` | `0` | Enable private `/v1/plesk/publish`; plan endpoint remains available. |
| `WELLMANIFEST_MAX_BODY_BYTES` | deployment-defined | Recommended ingress limit. |
| `MQTT_HOST` | `mqtt` | Bridge broker host. |
| `MQTT_TOPIC` | `wellmanifest/v1/+/request/+` | Bridge subscription. |

## Release outputs

A production release should publish:

- Python wheel/sdist;
- npm package;
- Rust crates;
- native CLI binaries with checksums;
- WASM package;
- multi-architecture OCI images;
- `.proto` and JSON Schemas;
- SBOM, provenance and conformance report.

Version 0.2.0rc2 packages source and build recipes; registry publication is not
performed by this artifact.

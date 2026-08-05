# Development workflow and Makefile

The Makefile is the supported developer entry point. It uses
`config/env-contract.json` as the source for `.env.example` and passes the same
`.env` to every Compose project.

## Setup

```bash
make setup       # .env + venv + all Python extras + JS dependencies
make setup-lite  # .env + venv + dev/MQTT/gRPC extras + JS dependencies
```

`make env-setup` creates `.env` only when it is absent. It never overwrites
local values. Regenerate and verify the public template with:

```bash
make env-sync
make env-check
```

## Main runtime

```bash
make up
make logs
make down
```

`make up` runs a Docker network preflight and starts the HTTP/WebSocket runtime,
MQTT bridge/broker, gRPC service and landing page. `make down` stops the same
project and removes orphan services.

## Three-layer IoT runtime

```bash
make iot-up
make iot-down
make iot-e2e
```

The IoT project starts frontend, backend, MQTT broker/bridge and firmware
simulator. Its E2E profile requires an acknowledged firmware result, healthy
backend and accessible frontend.

## Verification

```bash
make test          # Python + JavaScript unit/contract tests
make verify        # env/version drift, tests, governance, schema round-trip, TOON
make e2e-local     # local multi-client runtime test without Docker
make e2e-docker    # full Compose matrix
make e2e           # local + Docker matrix + IoT matrix
```

`make e2e` is fail-closed when Docker is missing. A local-only result must be
requested explicitly with `make e2e-local`. The optional variable
`WELLMANIFEST_E2E_ALLOW_LOCAL_FALLBACK=1` is accepted only by the standalone
`scripts/e2e.sh` compatibility entry point and is never the default Make target.

## Contract maintenance

```bash
make versions-sync
make versions-check
make governance
make governance-check
make schema-demo
make intent-demo
make todo2code-intent  # requires an installed t2c CLI
```

A format, API or schema change is incomplete until `versions-sync` has updated
both registry copies and `versions-check` passes. An environment variable change
is incomplete until `env-sync` and `env-check` pass.

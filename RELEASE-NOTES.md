# wellm 0.2.0rc4 release notes

Release date: 2026-08-05

## Main changes

This candidate turns the earlier multi-dialect runtime into a more controlled
platform release:

- a dedicated three-layer IoT topology for frontend, backend and firmware;
- one environment contract shared by Make, Compose and application code;
- one validated version registry for formats, profiles, APIs and schemas;
- exact JSON Schema ⇄ typed schema-module round-trip and static type generation;
- TOON/code2llm structural-map import;
- deterministic cross-format intent evidence for todo2code;
- explicit Docker IPAM and network preflight.

## Three-layer IoT

```bash
make iot-up
make iot-down
make iot-e2e
```

`compose.iot.yml` starts nginx/JavaScript frontend, FastAPI backend, Mosquitto,
Wellm MQTT bridge and a thin firmware/RPi simulator. The device asks for config
through `iot://device/config/query/get` and submits
`wellm.iot-telemetry/v1` to `iot://device/telemetry/command/ingest`.
Authority remains in the server-side contract.

## Make and environment

```bash
make setup
make up
make down
make verify
make e2e-local
make e2e
```

`config/env-contract.json` is the source for `.env.example`, validation and
runtime discovery. `make env-setup` is idempotent and does not overwrite an
existing `.env`. `make env-check` scans source, scripts, Dockerfiles, Compose and
Make references.

## Version control

```bash
make versions-sync
make versions-check
wellm versions
```

The registry tracks:

- 9 versioned dialects;
- 9 versioned formatting profiles;
- 4 hashed API contracts;
- every Draft 2020-12 schema with `$id`, contract, version, compatibility rule
  and exact SHA-256;
- Python, npm, Cargo and container package versions.

The generator validates all schemas and rejects duplicate or unversioned
identities. A defect discovered during release verification—generation of a
`null` registry—was fixed and covered by tests.

## Bidirectional typing

```bash
wellm schema import schemas/status.schema.json -o status.schema.wm
wellm schema export status.schema.wm -o status.schema.roundtrip.json
wellm schema codegen status.schema.wm --from typed --language typescript -o status.d.ts
wellm schema codegen status.schema.wm --from typed --language python -o status_types.py
```

The schema-module route preserves the complete Draft 2020-12 document exactly.
Data conversion can preserve, infer or derive type hints from a supplied schema.
A general compiler for every future free-form Wellm type declaration remains a
candidate surface and is not claimed as complete.

## todo2code and TOON

```bash
make intent-demo
wellm convert examples/toon/map.toon.yaml --from toon --to json
```

The intent demo validates six representations against one schema and emits a
pairwise semantic report plus `wellm.todo2code-format-evidence/v1`. The evidence
is suitable for deterministic `t2c extract config`, after which todo2code can
link it with Git, AST, TODO, changelog and documentation evidence.

## Docker network correction

The supplied prior E2E run built all service images but Docker then failed to
create the Compose network because all predefined address pools had been
subnetted. This candidate gives each Compose project an explicit configurable
CIDR and runs a collision preflight. The correction still requires a fresh
Docker run on the affected host for final confirmation.

## Compatibility

Public JSON/JSON Schema contracts remain available. Wellm sources can generate
canonical JSON without inserting metadata into closed records. The `wellm` and
legacy `wellmanifest` CLI/Python aliases remain available, as does the original
`well` compatibility API from `0.1.x`.

## Verification in the packaging environment

The final `TEST-REPORT.md` records exact executed counts. Docker and Rust checks
are reported separately and are never marked passed merely because their source
or Compose definitions exist.

# wellm / WellManifest 0.2.0rc4 test report

Generated: 2026-08-05T07:59:25Z

| Suite | Result |
|---|---|
| Python reference tests | 69/69 PASS (Python 3.13.5) |
| JavaScript SDK tests | 9/9 PASS (Node 22.16.0) |
| Local HTTP/Node/RPi E2E | PASS — HTTP, Node, RPi, Plesk parity, governance, versions/env/types/TOON/intent |
| Governance build/check | PASS — deterministic build/check; 2 source warnings retained |
| Environment contract | PASS — 65 declared variables; no unknown or duplicate names |
| Version/API/schema registry | PASS — 9 dialects, 9 profiles, 25 schemas, 4 APIs, 11 protocols |
| Bidirectional schema typing | PASS — exact JSON Schema ⇄ typed module and TypeScript/Python codegen |
| Multi-format intent/todo2code evidence | PASS — 6 formats, 15 pairs, schema-valid/equivalent; todo2code CLI bridge tested |
| Three-layer IoT | PASS for local contracts/runtime/firmware tests; Docker Compose target included but not run locally |
| Python wheel smoke | PASS — install/import/resources and installed `versions --check` |
| npm package smoke | PASS — tarball install/import and rc4 client API |
| Source ZIP smoke | PASS — ZIP/TAR integrity, no .env/caches, extracted checks |
| Ruff lint | NOT RUN — ruff command unavailable |
| Docker Compose E2E | NOT RUN locally — Docker CLI/engine unavailable; explicit IPAM/preflight awaits engine rerun |
| Rust/WASM/PyO3/N-API | NOT RUN locally — cargo/rustc unavailable |

Verification commands:

`./scripts/verify.sh`
`./scripts/e2e-local.sh`
`./scripts/e2e-docker.sh`

A source scaffold or Docker recipe is not marked as executed unless the
corresponding toolchain was available in the packaging environment.

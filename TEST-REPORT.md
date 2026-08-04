# WellManifest 0.1.0 test report

Generated: 2026-08-04T16:28:12Z

| Suite | Result |
|---|---|
| Python reference tests | PASS — 23/23 tests (Python 3.13.5) |
| JavaScript SDK tests | PASS — 4/4 tests (Node 22.16.0) |
| Local HTTP/Node/RPi E2E | PASS — HTTP conversion/validation, Node SDK, URI Process, RPi thin client, CQRS/ES events |
| Docker Compose E2E | NOT RUN — Docker CLI/engine unavailable in packaging environment; Compose matrix included |
| Rust/WASM/PyO3/N-API | NOT RUN — cargo/rustc unavailable in packaging environment; source and Docker CI targets included |

Verification commands:

`./scripts/verify.sh`
`./scripts/e2e-local.sh`
`./scripts/e2e-docker.sh`

A source scaffold or Docker recipe is not marked as executed unless the
corresponding toolchain was available in the packaging environment.

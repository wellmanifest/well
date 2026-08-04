# wellm / WellManifest 0.2.0rc2 test report

Generated: 2026-08-04T18:16:16Z

| Suite | Result |
|---|---|
| Python reference tests | 38/38 PASS (Python 3.13.5) |
| JavaScript SDK tests | 7/7 PASS (Node.js 22.16.0) |
| Local HTTP/Node/RPi E2E | PASS (HTTP, Node, Python/JS Plesk parity, RPi, Plesk plan, offline LLM benchmark, events) |
| Docker Compose E2E | NOT RUN — Docker CLI/engine unavailable in this environment |
| Rust/WASM/PyO3/N-API | NOT RUN — cargo/rustc unavailable in this environment |

Verification commands:

`./scripts/verify.sh`
`./scripts/e2e-local.sh`
`./scripts/e2e-docker.sh`

A source scaffold or Docker recipe is not marked as executed unless the
corresponding toolchain was available in the packaging environment.

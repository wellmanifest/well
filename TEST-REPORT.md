# wellm / WellManifest 0.2.0rc3 test report

Generated: 2026-08-04T21:54:48Z

| Suite | Result |
|---|---|
| Python reference tests | 54/54 PASS (Python 3.13) |
| JavaScript SDK tests | 8/8 PASS (Node 22.16.0) |
| Local HTTP/Node/RPi E2E | PASS: HTTP, Node, RPi, Plesk parity, benchmark, governance build/check |
| Governance build/check | PASS: 4 generated data artifacts CURRENT; policy IR CURRENT; 2 expected source warnings |
| Python wheel smoke | PASS: import, compatibility API, profiles and governance --check |
| npm package smoke | PASS: local tarball install, canonical JSON, semantic digest and client import |
| Source ZIP smoke | PASS: extracted ZIP governance/policy/format tests and SDK smoke |
| Ruff lint | NOT RUN: ruff unavailable |
| Docker Compose E2E | NOT RUN: Docker/Podman CLI unavailable |
| Rust/WASM/PyO3/N-API | NOT RUN: cargo/rustc unavailable |

Verification commands:

`./scripts/verify.sh`
`./scripts/e2e-local.sh`
`./scripts/e2e-docker.sh`

A source scaffold or Docker recipe is not marked as executed unless the
corresponding toolchain was available in the packaging environment.

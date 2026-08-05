# wellm 0.2.0rc3 release notes

Release date: 2026-08-04

## Main change

This release candidate adds `wellm-governance-profile@1`, allowing Wellm to be
the editable source format while existing validators, CI, adoption locks and
external consumers continue to receive deterministic JSON and JSON Schema
Draft 2020-12 artifacts.

## Included

- eight named formatting profiles;
- deterministic `repo-json@1` and compact `wire-json@1`;
- independent exact-byte and semantic SHA-256 digests;
- artifact metadata sidecars and JSON Pointer source maps;
- `wellm governance build` and fail-on-drift `--check`;
- `wellm fmt`, `profiles`, `semantic-diff` and `roundtrip`;
- policy Markdown import/lint/formatter with safe compatibility for
  policy-shaped `bash`, `sh` and `shell` fences;
- state-machine checks for duplicate identifiers and undeclared transitions;
- HTTP, WebSocket, URI Process and JavaScript SDK formatting/diff APIs;
- current and legacy governance fixtures based on the supplied repository
  contracts;
- generated manifest, intent, diagnostics, stack profiles, metadata, source
  maps and policy IR examples;
- CI, verification, E2E and landing-page integration.

## Compatibility strategy

Public `*.schema.json`, approval evidence, lock files and generated governance
JSON remain JSON. Wellm metadata is emitted next to governed files rather than
inserted into closed records. This avoids violating schemas with
`additionalProperties: false`.

## Deliberately reported source issues

The supplied policy document contains a policy-shaped block fenced as `bash`;
Wellm imports it and emits `WM-POLICY-101`. It also declares a transition to
`IN_PROGRESS` without declaring that workflow state; Wellm emits
`WM-POLICY-204` and does not guess whether a ticket status was intended.

## Validation performed in the build environment

- Python: 54 tests passed;
- JavaScript SDK: 8 tests passed;
- local multi-client E2E: passed;
- governance build/check: passed with the two expected source warnings;
- wheel import/API/governance smoke: passed;
- npm tarball import/API smoke: passed;
- extracted source ZIP smoke: passed.

Docker/Podman, Rust and Ruff were not available in the build environment, so
those checks are not claimed as executed. Corresponding CI and Compose
definitions remain included.

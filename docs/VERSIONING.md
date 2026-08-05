# Versioning contracts

Wellm keeps one generated registry at `config/version-registry.json`. The same
file is packaged in `wellmanifest/resources/version-registry.json` and exposed
through `GET /v1/versions` and `wellmanifest://runtime/versions/query`.

```bash
make versions-sync     # regenerate after a contract change
make versions-check    # fail when registry, identities or hashes drift
wellm versions         # print the current registry
```

## What is versioned

| Surface | Identity | Compatibility check |
|---|---|---|
| package | `wellm 0.2.0rc4` | exact package version |
| protocol | `wellmanifest.protocol/v1` | backward-compatible additions inside v1 |
| Core IR | `wellmanifest-ir/v1` | exact major |
| dialect | e.g. `typed@1`, `hcl@2`, `toon@1` | version embedded in dialect identifier |
| format profile | e.g. `repo-json@1`, `typescript-data@1` | exact profile major |
| HTTP API | `/v1`, OpenAPI 3.1 | API major + exact SHA-256 of `schemas/openapi.json` |
| WebSocket/MQTT | AsyncAPI 3.0 | API major + exact SHA-256 of `schemas/asyncapi.yaml` |
| gRPC | `wellmanifest.v1.RuntimeService` | service major + exact SHA-256 of the proto source |
| JSON Schema | `$id` + contract + version | Draft 2020-12 + exact file SHA-256 |
| Python/npm/Cargo/container | ecosystem + name | package version |

Every JSON Schema registry entry contains:

```json
{
  "path": "schemas/intent-format-analysis.schema.json",
  "id": "https://raw.githubusercontent.com/wellmanifest/wellm/v0.2.0rc4/schemas/intent-format-analysis.schema.json",
  "contract": "wellm.intent-format-analysis/v1",
  "version": "v1",
  "compatibility": "exact-major",
  "dialect": "json-schema@2020-12",
  "sha256": "sha256:..."
}
```

Schemas with a public `/vN` or `@N` contract use `exact-major`. Legacy schemas
without an explicit public major remain package-versioned and use `exact-hash`.
OpenAPI is not misclassified as JSON Schema; it is tracked in the API section.

## Enforcement

The registry generator:

- validates every discovered JSON Schema with Draft 2020-12;
- requires a non-empty `$id`;
- rejects duplicate protocol, API, dialect, profile, schema and package identities;
- rejects unversioned dialect/profile identifiers;
- rejects missing or unhashed API contracts;
- records every schema version, compatibility policy and content hash;
- fails `--check` when either generated registry copy differs.

## Compatibility policy

Adding an optional field or a new URI Process under an existing major is
backward compatible. Removing or changing the meaning of a required field,
renumbering a protobuf field, or changing canonical formatting requires a new
major contract/profile. Pre-release package versions can change implementation
details but may not silently change a published v1 wire contract.

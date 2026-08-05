# Bidirectional typing

Wellm supports two complementary round trips.

## Data round trip

```text
JSON/YAML/HCL/TypeScript/TOON
             + JSON Schema
                    ↓
             typed Wellm hints
                    ↓
        JSON/YAML/TypeScript/HCL
```

```bash
wellm convert intent.json --from json --to typed \
  --schema intent.schema.json --types schema
wellm convert intent.wm --from typed --to json
```

`--types` accepts:

- `preserve` — retain source annotations and enrich from a supplied schema;
- `schema` — derive annotations from JSON Schema;
- `infer` — infer structural scalar/list types without claiming nominal types;
- `none` — emit values without type annotations.

## Schema round trip

The schema module wrapper stores the exact JSON Schema 2020-12 document as a
normative typed value. This makes import/export exact even for `if/then`,
`allOf`, `oneOf`, tuple `prefixItems`, regexes and extension keywords.

```bash
wellm schema import schemas/status.schema.json -o status.schema.wm
wellm schema export status.schema.wm -o status.schema.roundtrip.json
wellm schema codegen status.schema.wm --from typed \
  --language typescript -o status.d.ts
wellm schema codegen status.schema.wm --from typed \
  --language python -o status_types.py
```

The exact wrapper round trip is complete. Human-authored free-form type
declarations are still a candidate language surface: in `0.2.0rc4` their data
annotations are parsed and preserved, while the normative full-schema reverse
path uses the embedded `JSONSchema202012` module.

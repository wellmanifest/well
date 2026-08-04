# Plesk publication example

The project registry is the source document. `@uri-twin/plesk` contributes a
reviewed, read-only capability/workflow baseline. `urirun-connector-plesk`
performs observations and the guarded publication.
 The generated preflight obtains read-only subscription and
docroot twin facts before capability checks and any publication plan.

```bash
wellm validate examples/plesk/projects.json --schema schemas/projects.schema.json
wellm plesk-plan examples/plesk/projects.json \
  --project obslugabiurowa-pl \
  --source-ref workspace:obslugabiurowa-pl=examples/plesk/site/www \
  --workspace-root . \
  --to yaml
```


Equivalent generated representations are included for import/export tests:

- `projects.json` — canonical input matching the requested configuration;
- `projects.yaml` — YAML 1.2 JSON-compatible projection;
- `projects.wm` — typed WellManifest data projection;
- `projects.hcl` — HCL-shaped data projection;
- `projects.wm.ts` — restricted TypeScript data module.

Regenerate them with:

```bash
wellm convert examples/plesk/projects.json --from json --to yaml -o examples/plesk/projects.yaml
wellm convert examples/plesk/projects.json --from json --to typed -o examples/plesk/projects.wm
wellm convert examples/plesk/projects.json --from json --to hcl -o examples/plesk/projects.hcl
wellm convert examples/plesk/projects.json --from json --to typescript -o examples/plesk/projects.wm.ts
```

Remote connector preflight and file/hash dry-run:

```bash
export URIRUN_NODE_URL=http://urirun-node:8080
export URIRUN_TOKEN=...
wellm plesk-publish examples/plesk/projects.extended.yaml \
  --project obslugabiurowa-pl \
  --source-ref workspace:obslugabiurowa-pl=examples/plesk/site/www \
  --workspace-root . \
  --node-url "$URIRUN_NODE_URL"
```

Apply is a separate operation and remains blocked without both values returned
by the trusted control plane:

```bash
export URIRUN_APPLY_GRANT='signed-single-use-grant'
wellm plesk-publish examples/plesk/projects.extended.yaml \
  --project obslugabiurowa-pl \
  --source-ref workspace:obslugabiurowa-pl=examples/plesk/site/www \
  --workspace-root . \
  --node-url "$URIRUN_NODE_URL" \
  --apply --plan-hash "$CONNECTOR_PLAN_HASH"
```

No Plesk password, API key or SFTP password belongs in the project manifest.
Only vault handles and HTTPS credential origins are accepted.

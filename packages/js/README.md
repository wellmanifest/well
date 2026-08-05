# @wellmanifest/wellm-sdk

Dependency-free HTTP, WebSocket and URI Process clients for browsers and
Node.js. The client performs early concrete-URI and scope checks, while the
trusted server remains the authority through a Contract AQL reference.

```js
import {WellManifestClient} from "@wellmanifest/wellm-sdk";

const client = new WellManifestClient({baseUrl: "http://localhost:8080"});
const result = await client.convert("status: ok", {from: "yaml", to: "json"});
```

## Plesk publication planning

```js
import {
  buildPleskPublicationPlan,
  validateProjectRegistry,
} from "@wellmanifest/wellm-sdk";

const registry = validateProjectRegistry(projects);
const plan = await buildPleskPublicationPlan(registry, {
  projectId: "obslugabiurowa-pl",
  sourceRefs: {
    "workspace:obslugabiurowa-pl": "/workspace/obslugabiurowa-pl/www",
  },
});

console.log(plan.manifest_hash, plan.allowed_uri_processes);
```

The helper creates a deterministic, non-executing plan. Remote effects should be
sent through the trusted WellManifest/urirun control boundary after server-side
schema, Contract AQL, plan-hash and apply-grant checks.

## Canonical urirun client

```js
import {UrirunProcessClient} from "@wellmanifest/wellm-sdk";

const client = new UrirunProcessClient({
  nodeUrl: "http://urirun-bridge:8080",
  token: process.env.URIRUN_TOKEN,
  contractRef: "contract:plesk-publication",
});

await client.execute(
  "plesk://host/doctor/query/report",
  {},
  {allowedUriProcesses: ["plesk://host/doctor/query/report"]},
);
```

A wildcard can appear in a permission scope, but never as the executable URI.


## Governance formatting and semantic digests

```js
import {
  canonicalJson,
  semanticDigest,
  WellManifestClient,
} from "@wellmanifest/wellm-sdk";

const digest = await semanticDigest({b: 2, a: 1});
// sha256:43258cff...

const client = new WellManifestClient({baseUrl: "http://localhost:8080"});
const profiles = await client.profiles();
const formatted = await client.format(
  {schema: "new-project.intent/v2", ticket: "ticket-002"},
  {profile: "repo-json@1"},
);
const diff = await client.semanticDiff(previousManifest, currentManifest);
```

`canonicalJson()` and `semanticDigest()` are local helpers for JSON-compatible
data. Schema-aware repository formatting, source maps and governance
`build --check` remain server/CLI operations.

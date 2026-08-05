import assert from "node:assert/strict";
import test from "node:test";

import {assertConcreteUri, canonicalJson, createEnvelope, matchesUriProcess, semanticDigest, UrirunProcessClient, WellManifestClient} from "../src/index.js";

test("URI scopes are prefix capabilities, not executable wildcard URIs", () => {
  assert.equal(matchesUriProcess("youtube://channel/video/query/list", ["youtube://*"]), true);
  assert.equal(matchesUriProcess("flow://host/run", ["youtube://*"]), false);
  assert.throws(() => assertConcreteUri("youtube://*"), /uri_process_uri_invalid/);
});

test("createEnvelope emits the canonical protocol fields", () => {
  const envelope = createEnvelope({operation: "youtube://channel/video/query/list", payload: {channel: "ours"}});
  assert.equal(envelope.spec, "wellmanifest.protocol/v1");
  assert.equal(envelope.runtime.environment, "frontend");
  assert.deepEqual(envelope.payload, {channel: "ours"});
});

test("HTTP client uses the conversion endpoint", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({url, init});
    return new Response(JSON.stringify({output: "{}", diagnostics: []}), {status: 200});
  };
  const client = new WellManifestClient({baseUrl: "http://runtime", fetchImpl});
  await client.convert({hello: "world"}, {to: "yaml"});
  assert.equal(calls[0].url, "http://runtime/v1/convert");
});

test("urirun client rejects a request before network contact when scope does not match", async () => {
  let called = false;
  const client = new UrirunProcessClient({
    nodeUrl: "http://runtime",
    fetchImpl: async () => { called = true; throw new Error("unexpected"); },
  });
  await assert.rejects(
    client.execute("youtube://channel/video/query/list", {}, {allowedUriProcesses: ["flow://*"]}),
    /uri_process_not_allowed/,
  );
  assert.equal(called, false);
});

import {buildPleskPublicationPlan, validateProjectRegistry} from "../src/index.js";

const projectRegistry = {
  schema: "subactor.projects/v1",
  projects: [{
    id: "obslugabiurowa-pl",
    company: "ObsługaBiurowa.pl",
    domain: "obslugabiurowa.pl",
    subscription: "prototypowanie.pl",
    dns_zone: "obslugabiurowa.pl",
    dns_provider: "cloudflare",
    dns_management_plane: "plesk",
    dns_sync_extension: "cloudflaredns",
    public_ingress_mode: "plesk_public_origin",
    tunnel_mode: "none",
    origin_ip: "217.160.250.222",
    source: "site",
    entrypoint: "index.html",
    publication: {
      mode: "static_httpdocs",
      publish_uri: "plesk://host/site/command/sync",
      verify_uri: "plesk://host/site/command/publish-verify",
      source_ref: "workspace:obslugabiurowa-pl",
      deployment_ref: "deployment:obslugabiurowa-pl:production",
      verification: {mode: "content_hash", path: "/"},
    },
    gates: ["subscription_can_create_domain", "dns_ready", "tls_ready"],
  }],
};

test("Plesk project registry and frontend planner preserve least-privilege exact URIs", async () => {
  assert.equal(validateProjectRegistry(projectRegistry), projectRegistry);
  const plan = await buildPleskPublicationPlan(projectRegistry, {
    projectId: "obslugabiurowa-pl",
    sourceRefs: {"workspace:obslugabiurowa-pl": "/workspace/obslugabiurowa-pl/www"},
  });
  assert.equal(plan.project_id, "obslugabiurowa-pl");
  assert.match(plan.manifest_hash, /^[a-f0-9]{64}$/);
  assert.equal(plan.steps.find((step) => step.id === "publish-dry-run").payload.apply, false);
  assert.equal(plan.allowed_uri_processes.some((uri) => uri.includes("*")), false);
  assert.equal(plan.twin.mode, "read-only");
  assert.equal(plan.diagnostics.some((item) => item.code === "WM-TWIN-101"), true);
  assert.ok(plan.allowed_uri_processes.includes("plesk://host/subscription/query/snapshot"));
  assert.ok(plan.allowed_uri_processes.includes("plesk://host/site/query/docroot"));
});

test("urirun client sends the canonical urirun token header", async () => {
  let headers;
  const client = new UrirunProcessClient({
    nodeUrl: "http://runtime",
    token: "secret",
    fetchImpl: async (_url, init) => {
      headers = init.headers;
      return new Response(JSON.stringify({ok: true, result: {value: {ok: true}}}), {status: 200});
    },
  });
  await client.execute("plesk://host/doctor/query/report", {}, {allowedUriProcesses: ["plesk://*"]});
  assert.equal(headers["x-urirun-token"], "secret");
});


test("Plesk frontend planner applies protocol defaults to the minimal project registry", async () => {
  const minimal = {
    schema: "subactor.projects/v1",
    projects: [{
      id: "demo",
      company: "Demo",
      domain: "example.com",
      subscription: "example.com",
      dns_zone: "example.com",
      dns_provider: "cloudflare",
      dns_management_plane: "plesk",
      public_ingress_mode: "plesk_public_origin",
      tunnel_mode: "none",
      origin_ip: "192.0.2.10",
      publication: {
        source_ref: "workspace:demo",
        deployment_ref: "deployment:demo:production",
      },
    }],
  };
  validateProjectRegistry(minimal);
  const plan = await buildPleskPublicationPlan(minimal, {
    projectId: "demo",
    sourceRefs: {"workspace:demo": "/workspace/demo/www"},
  });
  assert.equal(plan.steps.length, 10);
  assert.equal(plan.steps.find((step) => step.id === "publish-dry-run").uri, "plesk://host/site/command/sync");
  assert.equal(plan.steps.find((step) => step.id === "publish-verify").uri, "plesk://host/site/command/publish-verify");
});


test("canonical JSON and semantic digest ignore object key order", async () => {
  const left = {b: 2, a: {z: true, y: [1, 2]}};
  const right = {a: {y: [1, 2], z: true}, b: 2};
  assert.equal(canonicalJson(left), canonicalJson(right));
  assert.equal(await semanticDigest(left), await semanticDigest(right));
  assert.equal(
    await semanticDigest({b: 2, a: 1}),
    "sha256:43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777",
  );
});

test("client exposes version, env and intent-analysis contracts", async () => {
  const calls = [];
  const fetchImpl = async (url, init = {}) => {
    calls.push({url, init});
    if (url.endsWith("/v1/versions")) {
      return new Response(JSON.stringify({schema: "wellm.version-registry/v1", package: {version: "0.2.0rc4"}}), {status: 200});
    }
    if (url.endsWith("/v1/env-contract")) {
      return new Response(JSON.stringify({schema: "wellm.env-contract/v1", variables: []}), {status: 200});
    }
    return new Response(JSON.stringify({schema: "wellm.intent-format-analysis/v1", equivalent: true}), {status: 200});
  };
  const client = new WellManifestClient({baseUrl: "http://runtime", fetchImpl});
  assert.equal((await client.versions()).package.version, "0.2.0rc4");
  assert.equal((await client.envContract()).schema, "wellm.env-contract/v1");
  assert.equal((await client.analyzeIntent({id: "demo", representations: []})).equivalent, true);
  assert.deepEqual(calls.map((call) => call.url), [
    "http://runtime/v1/versions",
    "http://runtime/v1/env-contract",
    "http://runtime/v1/intent/analyze",
  ]);
});

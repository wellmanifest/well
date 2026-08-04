import assert from "node:assert/strict";
import test from "node:test";

import {assertConcreteUri, createEnvelope, matchesUriProcess, UrirunProcessClient, WellManifestClient} from "../src/index.js";

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

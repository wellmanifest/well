import assert from "node:assert/strict";
import {WellManifestClient, UrirunProcessClient} from "../packages/js/src/index.js";

const baseUrl = process.env.WELLMANIFEST_URL || "http://runtime:8080";
const client = new WellManifestClient({baseUrl, timeoutMs: 10000});

const capabilities = await client.capabilities();
assert.equal(capabilities.protocol, "wellmanifest.protocol/v1");

const converted = await client.convert("status:\n  value: SUCCEEDED\n  errors: []\n", {from: "yaml", to: "json"});
const output = JSON.parse(converted.output);
assert.equal(output.status.value, "SUCCEEDED");

const urirun = new UrirunProcessClient({nodeUrl: baseUrl, contractRef: "contract:dev"});
const executed = await urirun.execute(
  "youtube://channel/video/query/list",
  {channel: "ours"},
  {allowedUriProcesses: ["youtube://*"], runId: "docker-node:youtube:1"},
);
assert.equal(executed.ok, true);
console.log("node e2e: PASS");

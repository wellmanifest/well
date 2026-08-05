import assert from "node:assert/strict";
import {WellManifestClient, UrirunProcessClient} from "../packages/js/src/index.js";

const baseUrl = process.env.WELLMANIFEST_URL || "http://runtime:8080";
const client = new WellManifestClient({baseUrl, timeoutMs: 10000});

const capabilities = await client.capabilities();
assert.equal(capabilities.protocol, "wellmanifest.protocol/v1");
const versions = await client.versions();
assert.equal(versions.package.version, "0.2.0rc4");
const envContract = await client.envContract();
assert.equal(envContract.schema, "wellm.env-contract/v1");

const converted = await client.convert("status:\n  value: SUCCEEDED\n  errors: []\n", {from: "yaml", to: "json"});
const output = JSON.parse(converted.output);
assert.equal(output.status.value, "SUCCEEDED");
const intent = await client.analyzeIntent([
  {id: "json", dialect: "json", source: '{"schema":"example/v1"}'},
  {id: "yaml", dialect: "yaml", source: "schema: example/v1\n"},
]);
assert.equal(intent.equivalent, true);

const urirun = new UrirunProcessClient({nodeUrl: baseUrl, contractRef: "contract:dev"});
const executed = await urirun.execute(
  "youtube://channel/video/query/list",
  {channel: "ours"},
  {allowedUriProcesses: ["youtube://*"], runId: "docker-node:youtube:1"},
);
assert.equal(executed.ok, true);
console.log("node e2e: PASS");

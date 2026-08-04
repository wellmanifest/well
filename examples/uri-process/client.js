import {UrirunProcessClient} from "../../packages/js/src/index.js";

const client = new UrirunProcessClient({
  nodeUrl: process.env.URIRUN_NODE_URL || "http://localhost:8080",
  token: process.env.WELLMANIFEST_TOKEN || "",
  contractRef: "contract:dev",
});

const result = await client.execute(
  "youtube://channel/video/query/list",
  {channel: "ours"},
  {
    allowedUriProcesses: ["youtube://*"],
    runId: "ticket-002:youtube-list:1",
  },
);

console.log(JSON.stringify(result, null, 2));

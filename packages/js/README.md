# @wellmanifest/sdk

Dependency-free HTTP, WebSocket and URI Process clients for browsers and Node.js.
The client performs early concrete-URI and scope checks, while the server remains
the authority through a Contract AQL reference.

```js
import {WellManifestClient} from "@wellmanifest/sdk";

const client = new WellManifestClient({baseUrl: "http://localhost:8080"});
const result = await client.convert("status: ok", {from: "yaml", to: "json"});
```

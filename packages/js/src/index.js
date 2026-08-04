const CONCRETE_URI = /^[a-z][a-z0-9+.-]*:\/\/[^\s*]+$/i;
const SAFE_RUN_ID = /^[a-z0-9._:-]{1,160}$/i;

export function matchesUriProcess(uri, scopes = []) {
  const candidate = String(uri || "");
  return scopes.some((scope) => {
    const pattern = String(scope || "");
    if (pattern === "*") return true;
    if (pattern.endsWith("*")) return candidate.startsWith(pattern.slice(0, -1));
    return candidate === pattern;
  });
}

export function assertConcreteUri(uri) {
  const value = String(uri || "");
  if (!CONCRETE_URI.test(value) || value.includes("*")) throw new Error("uri_process_uri_invalid");
  return value;
}

export function createEnvelope({
  kind = "command",
  operation,
  payload = {},
  contentType = "application/wellmanifest+json",
  accept = ["application/wellmanifest+json"],
  contractRef = "",
  runtime = {},
  id = globalThis.crypto?.randomUUID?.() || `wm-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  idempotencyKey = "",
  metadata = {},
} = {}) {
  return {
    spec: "wellmanifest.protocol/v1",
    id,
    correlation_id: null,
    causation_id: null,
    timestamp: new Date().toISOString(),
    kind,
    operation: assertConcreteUri(operation),
    content_type: contentType,
    accept,
    schema_ref: null,
    contract_ref: contractRef || null,
    idempotency_key: idempotencyKey || null,
    runtime: {
      runtime_ref: runtime.runtimeRef || runtime.runtime_ref || "runtime:frontend-wasm@1",
      environment: runtime.environment || "frontend",
      execution: runtime.execution || "remote",
      resources: runtime.resources || {},
    },
    payload,
    diagnostics: [],
    metadata,
  };
}

export class WellManifestClient {
  constructor({baseUrl, token = "", timeoutMs = 15000, fetchImpl = globalThis.fetch} = {}) {
    this.baseUrl = String(baseUrl || "").replace(/\/$/, "");
    this.token = String(token || "");
    this.timeoutMs = Number(timeoutMs) || 15000;
    this.fetch = fetchImpl;
  }

  async request(path, body = undefined, {method = "POST"} = {}) {
    if (!this.baseUrl) throw new Error("wellmanifest_base_url_not_configured");
    if (typeof this.fetch !== "function") throw new Error("wellmanifest_fetch_not_available");
    const response = await this.fetch(`${this.baseUrl}${path}`, {
      method,
      headers: {
        accept: "application/json",
        ...(body === undefined ? {} : {"content-type": "application/json"}),
        ...(this.token ? {"x-wellmanifest-token": this.token} : {}),
      },
      ...(body === undefined ? {} : {body: JSON.stringify(body)}),
      signal: AbortSignal.timeout(this.timeoutMs),
    });
    const text = await response.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; } catch { data = {raw: text}; }
    if (!response.ok) {
      const error = new Error(`wellmanifest_http_${response.status}`);
      error.status = response.status;
      error.details = data;
      throw error;
    }
    return data;
  }

  capabilities() {
    return this.request("/v1/capabilities", undefined, {method: "GET"});
  }

  convert(source, {from = "auto", to = "json", projection = "data", schema = null, pretty = true} = {}) {
    return this.request("/v1/convert", {
      source,
      source_dialect: from,
      target_dialect: to,
      projection,
      schema,
      pretty,
    });
  }

  validate(source, schema, {dialect = "auto"} = {}) {
    return this.request("/v1/validate", {source, dialect, schema});
  }

  execute(uri, payload = {}, {
    mode = "execute",
    contractRef = "contract:dev",
    allowedUriProcesses = [],
    runId = "",
    runtime = {},
  } = {}) {
    const concreteUri = assertConcreteUri(uri);
    if (runId && !SAFE_RUN_ID.test(runId)) throw new Error("uri_process_run_id_invalid");
    return this.request("/v1/runtime/execute", {
      uri: concreteUri,
      payload,
      mode,
      contract_ref: contractRef || null,
      allowed_uri_processes: allowedUriProcesses,
      run_id: runId,
      runtime: {
        runtime_ref: runtime.runtimeRef || "runtime:remote-service@1",
        environment: runtime.environment || "remote",
        execution: runtime.execution || "remote",
        resources: runtime.resources || {},
      },
    });
  }

  exchange(envelope) {
    return this.request("/v1/envelopes", envelope);
  }
}

// Compatibility client for the canonical urirun node endpoint supplied by the
// URI Process design. Client-side scope checks are an early rejection only;
// production authority still comes from the server-side Contract AQL.
export class UrirunProcessClient {
  constructor({nodeUrl, token = "", contractRef = "contract:dev", timeoutMs = 15000, fetchImpl = globalThis.fetch} = {}) {
    this.nodeUrl = String(nodeUrl || "").replace(/\/$/, "");
    this.token = String(token || "");
    this.contractRef = String(contractRef || "");
    this.timeoutMs = timeoutMs;
    this.fetch = fetchImpl;
  }

  async execute(uri, payload = {}, {mode = "execute", allowedUriProcesses = [], runId = ""} = {}) {
    if (!this.nodeUrl) throw new Error("urirun_node_not_configured");
    const concreteUri = assertConcreteUri(uri);
    if (!matchesUriProcess(concreteUri, allowedUriProcesses)) throw new Error("uri_process_not_allowed");
    const correlatedRunId = String(runId || "");
    if (correlatedRunId && !SAFE_RUN_ID.test(correlatedRunId)) throw new Error("uri_process_run_id_invalid");
    const response = await this.fetch(`${this.nodeUrl}/run`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(this.token ? {"x-wellmanifest-token": this.token} : {}),
        ...(this.contractRef ? {"x-wellmanifest-contract": this.contractRef} : {}),
        ...(correlatedRunId ? {"x-urirun-run-id": correlatedRunId} : {}),
      },
      body: JSON.stringify({uri: concreteUri, mode, payload: payload || {}}),
      signal: AbortSignal.timeout(this.timeoutMs),
    });
    const text = await response.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; } catch { data = {raw: text}; }
    if (!response.ok) {
      const error = new Error(`urirun_node_${response.status}`);
      error.status = response.status;
      error.details = data;
      throw error;
    }
    const handlerValue = data?.result?.value;
    if (handlerValue && typeof handlerValue === "object" && handlerValue.ok === false) {
      const reason = String(handlerValue.error || handlerValue.reason || "urirun_handler_failed");
      const error = new Error(reason);
      error.code = "urirun_handler_failed";
      error.status = Number(handlerValue.status) >= 400 && Number(handlerValue.status) <= 599
        ? Number(handlerValue.status)
        : 422;
      error.details = handlerValue;
      throw error;
    }
    return data;
  }
}

export class WellManifestWebSocket {
  constructor({url, token = "", WebSocketImpl = globalThis.WebSocket} = {}) {
    this.url = String(url || "");
    this.token = token;
    this.WebSocketImpl = WebSocketImpl;
    this.socket = null;
    this.pending = new Map();
  }

  connect() {
    if (!this.WebSocketImpl) throw new Error("wellmanifest_websocket_not_available");
    const separator = this.url.includes("?") ? "&" : "?";
    this.socket = new this.WebSocketImpl(`${this.url}${this.token ? `${separator}token=${encodeURIComponent(this.token)}` : ""}`, "wellmanifest.v1");
    this.socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (!message.id || !this.pending.has(message.id)) return;
      const {resolve} = this.pending.get(message.id);
      this.pending.delete(message.id);
      resolve(message.result);
    });
    return new Promise((resolve, reject) => {
      this.socket.addEventListener("open", resolve, {once: true});
      this.socket.addEventListener("error", reject, {once: true});
    });
  }

  call(op, request) {
    if (!this.socket || this.socket.readyState !== this.WebSocketImpl.OPEN) throw new Error("wellmanifest_websocket_not_connected");
    const id = globalThis.crypto?.randomUUID?.() || `ws-${Date.now()}-${Math.random()}`;
    return new Promise((resolve, reject) => {
      this.pending.set(id, {resolve, reject});
      this.socket.send(JSON.stringify({id, op, request}));
    });
  }

  close() {
    this.socket?.close();
  }
}

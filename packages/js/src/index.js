const CONCRETE_URI = /^[a-z][a-z0-9+.-]*:\/\/[^\s*]+$/i;
const SAFE_RUN_ID = /^[a-z0-9._:-]{1,160}$/i;

export function canonicalizeData(value, path = "$") {
  if (value === null || typeof value === "boolean" || typeof value === "string") {
    return typeof value === "string" ? value.normalize("NFC") : value;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error(`wellmanifest_non_finite_number:${path}`);
    return Object.is(value, -0) ? 0 : value;
  }
  if (Array.isArray(value)) {
    return value.map((item, index) => canonicalizeData(item, `${path}/${index}`));
  }
  if (value && typeof value === "object") {
    const result = {};
    for (const originalKey of Object.keys(value).sort()) {
      const key = originalKey.normalize("NFC");
      if (Object.prototype.hasOwnProperty.call(result, key)) {
        throw new Error(`wellmanifest_duplicate_normalized_key:${path}/${key}`);
      }
      result[key] = canonicalizeData(value[originalKey], `${path}/${key}`);
    }
    return result;
  }
  throw new Error(`wellmanifest_json_incompatible:${path}`);
}

export function canonicalJson(value) {
  return JSON.stringify(canonicalizeData(value));
}

export async function semanticDigest(value) {
  const bytes = new TextEncoder().encode(canonicalJson(value));
  let subtle = globalThis.crypto?.subtle;
  if (!subtle && typeof process !== "undefined" && process.versions?.node) {
    const crypto = await import("node:crypto");
    subtle = crypto.webcrypto.subtle;
  }
  if (!subtle) throw new Error("wellmanifest_crypto_subtle_not_available");
  const digest = await subtle.digest("SHA-256", bytes);
  const hex = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `sha256:${hex}`;
}

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

  profiles() {
    return this.request("/v1/profiles", undefined, {method: "GET"});
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

  format(value, {profile = "repo-json@1", schema = null} = {}) {
    return this.request("/v1/format", {value, profile, schema});
  }

  semanticDiff(left, right) {
    return this.request("/v1/semantic-diff", {left, right});
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

  planPlesk(config, {projectId, sourceRefs = {}} = {}) {
    return this.request("/v1/plesk/plan", {config, project_id: projectId, source_refs: sourceRefs});
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
        ...(this.token ? {"x-urirun-token": this.token, "x-wellmanifest-token": this.token} : {}),
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


function assertNoEmbeddedSecrets(value, path = "$") {
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    const lowered = key.toLowerCase();
    const isHandle = lowered.endsWith("_vault_entry_id") || lowered.endsWith("_ref") || lowered === "vault_url";
    if (!isHandle && /(password|secret|api[_-]?key|access[_-]?token|private[_-]?key)/i.test(lowered)) {
      throw new Error(`wellmanifest_secret_field_forbidden:${path}.${key}`);
    }
    assertNoEmbeddedSecrets(child, `${path}.${key}`);
  }
}

function sortedValue(value) {
  if (Array.isArray(value)) return value.map(sortedValue);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, sortedValue(value[key])]));
}

async function sha256Hex(value) {
  const bytes = new TextEncoder().encode(JSON.stringify(sortedValue(value)));
  if (!globalThis.crypto?.subtle) throw new Error("wellmanifest_crypto_subtle_not_available");
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function validateProjectRegistry(registry) {
  assertNoEmbeddedSecrets(registry);
  if (!registry || registry.schema !== "subactor.projects/v1" || !Array.isArray(registry.projects)) {
    throw new Error("wellmanifest_project_registry_invalid");
  }
  const ids = new Set();
  for (const project of registry.projects) {
    if (!project?.id || ids.has(project.id)) throw new Error("wellmanifest_project_id_invalid_or_duplicate");
    ids.add(project.id);
    for (const key of ["domain", "subscription", "dns_zone", "origin_ip"]) {
      if (!project[key]) throw new Error(`wellmanifest_project_field_missing:${key}`);
    }
    const publication = project.publication;
    if (!publication?.source_ref || !publication?.deployment_ref) throw new Error("wellmanifest_publication_invalid");
    assertConcreteUri(publication.publish_uri || "plesk://host/site/command/sync");
    assertConcreteUri(publication.verify_uri || "plesk://host/site/command/publish-verify");
    if (publication.transport === "ftp") throw new Error("wellmanifest_unsafe_ftp_publication_profile");
  }
  return registry;
}

export async function buildPleskPublicationPlan(registryInput, {projectId, sourceRefs = {}} = {}) {
  const registry = validateProjectRegistry(registryInput);
  const project = registry.projects.find((item) => item.id === projectId);
  if (!project) throw new Error("wellmanifest_project_not_found");
  const publicationInput = project.publication;
  const publication = {
    mode: "static_httpdocs",
    publish_uri: "plesk://host/site/command/sync",
    verify_uri: "plesk://host/site/command/publish-verify",
    remote_path: "/httpdocs",
    transport: "sftp",
    sftp_port: 22,
    sftp_vault_entry_id: "plesk-sftp",
    ...publicationInput,
    verification: {
      mode: "content_hash",
      path: "/",
      expected_http_status: 200,
      ...(publicationInput.verification || {}),
    },
  };
  const sourceDir = sourceRefs[publication.source_ref];
  if (!sourceDir) throw new Error("wellmanifest_source_ref_unresolved");
  const connector = {
    package: "urirun-connector-plesk",
    repository: "https://github.com/urirun-connectors/urirun-connector-plesk",
    contract_ref: "contract:plesk-publication",
    node_url: null,
    ...(registry.connector || {}),
  };
  const twin = {
    package: "@uri-twin/plesk",
    repository: "https://github.com/uri-twin/uri-twin-plesk",
    mode: "read-only",
    revision: null,
    attestation_required: true,
    ...(registry.twin || {}),
  };
  const panel = Object.fromEntries(
    ["base_url", "subscription_vault_entry_id", "runtime_vault_entry_id", "vault_url"]
      .filter((key) => publication[key] != null)
      .map((key) => [key, publication[key]]),
  );
  const syncPayload = {
    source_dir: String(sourceDir),
    remote_path: publication.remote_path || "/httpdocs",
    host: publication.sftp_host || project.subscription,
    domain: project.domain,
    transport: publication.transport || "sftp",
    sftp_port: publication.sftp_port || 22,
    sftp_vault_entry_id: publication.sftp_vault_entry_id || "plesk-sftp",
    apply: false,
  };
  for (const key of ["credential_origin", "host_fingerprint", "actor", "pack_id", "pack_version"]) {
    if (publication[key] != null) syncPayload[key] = publication[key];
  }
  const expected = {dns_targets: [project.origin_ip], tls_hostname: project.domain};
  if (publication.verification.content_sha256) expected.content_sha256 = publication.verification.content_sha256;
  const steps = [
    {id: "connector-ready", title: "Read Plesk connector readiness", uri: "plesk://host/doctor/query/report", mode: "query", phase: "preflight", payload: {}, depends_on: [], gate: "connector_ready", mutation: false, human_approval: false},
    {id: "subscription-twin-fact", title: "Observe the subscription as a read-only URI Twin fact", uri: "plesk://host/subscription/query/snapshot", mode: "query", phase: "preflight", payload: {subscription: project.subscription, ...panel}, depends_on: ["connector-ready"], gate: null, mutation: false, human_approval: false},
    {id: "site-docroot-twin-fact", title: "Observe the live site docroot as a read-only URI Twin fact", uri: "plesk://host/site/query/docroot", mode: "query", phase: "preflight", payload: {domain: project.domain, ...panel}, depends_on: ["connector-ready"], gate: null, mutation: false, human_approval: false},
    {id: "subscription-capabilities", title: "Check whether the subscription can host the project domain", uri: "plesk://host/subscription/query/capabilities", mode: "query", phase: "preflight", payload: {subscription: project.subscription, ...panel}, depends_on: ["subscription-twin-fact"], gate: "subscription_can_create_domain", mutation: false, human_approval: false},
    {id: "dns-authority", title: "Observe the authoritative DNS provider and consistency", uri: "plesk://host/dns/query/authority", mode: "query", phase: "preflight", payload: {zone: project.dns_zone}, depends_on: ["connector-ready"], gate: "dns_authority_ready", mutation: false, human_approval: false},
    {id: "dns-propagation", title: "Check public DNS propagation for the origin address", uri: "plesk://host/dns/query/propagation", mode: "query", phase: "preflight", payload: {host: project.domain, record_type: "A", expected_value: project.origin_ip}, depends_on: ["dns-authority"], gate: "dns_ready", mutation: false, human_approval: false},
    {id: "tls-probe", title: "Probe origin TLS without mutation", uri: "plesk://host/site/command/ssl-ensure", mode: "dry-run", phase: "preflight", payload: {hostname: project.domain, origin_ip: project.origin_ip, provider: "auto", apply: false, ...panel}, depends_on: ["dns-propagation"], gate: "tls_ready", mutation: false, human_approval: false},
    {id: "publish-dry-run", title: "Build the connector file/hash plan without uploading", uri: publication.publish_uri, mode: "dry-run", phase: "plan", payload: syncPayload, depends_on: ["subscription-capabilities", "site-docroot-twin-fact", "dns-propagation", "tls-probe"], gate: "publish_plan_ready", mutation: false, human_approval: false},
    {id: "publish-apply", title: "Apply the exact connector plan after an explicit signed grant", uri: publication.publish_uri, mode: "command", phase: "apply", payload: syncPayload, depends_on: ["publish-dry-run"], gate: null, mutation: true, human_approval: true},
    {id: "publish-verify", title: "Verify DNS, TLS, HTTPS and content fingerprint", uri: publication.verify_uri, mode: "command", phase: "verify", payload: {hostname: project.domain, origin_ip: project.origin_ip, path: publication.verification.path, expected, expected_https_status: publication.verification.expected_http_status, verification_mode: publication.verification.mode, deployment_ref: publication.deployment_ref, ...(publication.verification.marker ? {expected_marker: publication.verification.marker} : {})}, depends_on: ["publish-apply"], gate: "publication_verified", mutation: false, human_approval: false},
  ];
  const diagnostics = [];
  if (twin.attestation_required && !twin.revision) {
    diagnostics.push({
      code: "WM-TWIN-101",
      severity: "WARNING",
      message: "The URI Twin baseline is not pinned to an exact verified revision; the production control plane must supply and attest one before autonomous apply.",
      phase: "plan",
      dialect: null,
      path: "/twin/revision",
      schema_path: null,
      source: null,
      range: null,
      hint: null,
      details: {},
    });
  }
  const plan = {
    schema: "wellmanifest.plesk-publication-plan/v1",
    id: `publication:${project.id}:${publication.deployment_ref}`,
    project_id: project.id,
    deployment_ref: publication.deployment_ref,
    created_at: new Date().toISOString(),
    source_ref: publication.source_ref,
    source_dir: String(sourceDir),
    entrypoint: project.entrypoint || "index.html",
    contract_ref: connector.contract_ref,
    connector,
    twin,
    allowed_uri_processes: [...new Set(steps.map((step) => step.uri))],
    required_gates: [...new Set(["connector_ready", ...(project.gates || []), "publish_plan_ready"])],
    steps,
    diagnostics,
  };
  const hashPayload = {...plan};
  delete hashPayload.created_at;
  delete hashPayload.diagnostics;
  plan.manifest_hash = await sha256Hex(hashPayload);
  return plan;
}

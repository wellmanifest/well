export type Dialect = "json" | "yaml" | "toml" | "hcl" | "typed" | "policy" | "proto3" | "typescript" | string;
export type Severity = "ERROR" | "WARNING" | "INFO";

export interface Diagnostic {
  code: string;
  severity: Severity;
  message: string;
  phase?: string;
  dialect?: string | null;
  path?: string | null;
  schema_path?: string | null;
  hint?: string | null;
  details?: Record<string, unknown>;
}

export interface RuntimeTarget {
  runtimeRef?: string;
  runtime_ref?: string;
  environment?: "frontend" | "backend" | "firmware" | "rpi" | "iot" | "digital-twin" | "server" | "remote";
  execution?: "local" | "remote" | "auto";
  resources?: Record<string, unknown>;
}

export interface Envelope<T = unknown> {
  spec: "wellmanifest.protocol/v1";
  id: string;
  correlation_id: string | null;
  causation_id: string | null;
  timestamp: string;
  kind: "command" | "query" | "event" | "result" | "diagnostic" | "handshake";
  operation: string;
  content_type: string;
  accept: string[];
  schema_ref: string | null;
  contract_ref: string | null;
  idempotency_key: string | null;
  runtime: {runtime_ref: string; environment: string; execution: string; resources: Record<string, unknown>};
  payload: T;
  diagnostics: Diagnostic[];
  metadata: Record<string, unknown>;
}

export function canonicalizeData<T = unknown>(value: T, path?: string): T;
export function canonicalJson(value: unknown): string;
export function semanticDigest(value: unknown): Promise<string>;
export function matchesUriProcess(uri: string, scopes?: string[]): boolean;
export function assertConcreteUri(uri: string): string;
export function createEnvelope<T = unknown>(options: {
  kind?: Envelope["kind"];
  operation: string;
  payload?: T;
  contentType?: string;
  accept?: string[];
  contractRef?: string;
  runtime?: RuntimeTarget;
  id?: string;
  idempotencyKey?: string;
  metadata?: Record<string, unknown>;
}): Envelope<T>;

export class WellManifestClient {
  constructor(options: {baseUrl: string; token?: string; timeoutMs?: number; fetchImpl?: typeof fetch});
  capabilities(): Promise<Record<string, unknown>>;
  profiles(): Promise<Array<Record<string, unknown>>>;
  convert(source: unknown, options?: {from?: Dialect; to?: Dialect; projection?: "data" | "ir"; schema?: object | null; pretty?: boolean}): Promise<Record<string, unknown>>;
  validate(source: unknown, schema: object, options?: {dialect?: Dialect}): Promise<Record<string, unknown>>;
  format(value: unknown, options?: {profile?: string; schema?: object | null}): Promise<Record<string, unknown>>;
  semanticDiff(left: unknown, right: unknown): Promise<Record<string, unknown>>;
  execute(uri: string, payload?: unknown, options?: {mode?: string; contractRef?: string; allowedUriProcesses?: string[]; runId?: string; runtime?: RuntimeTarget}): Promise<Record<string, unknown>>;
  exchange(envelope: Envelope): Promise<Envelope>;
  planPlesk(config: ProjectRegistry, options: {projectId: string; sourceRefs?: Record<string, string>}): Promise<PleskPublicationPlan>;
}

export class UrirunProcessClient {
  constructor(options: {nodeUrl: string; token?: string; contractRef?: string; timeoutMs?: number; fetchImpl?: typeof fetch});
  execute(uri: string, payload?: unknown, options?: {mode?: string; allowedUriProcesses?: string[]; runId?: string}): Promise<Record<string, unknown>>;
}

export class WellManifestWebSocket {
  constructor(options: {url: string; token?: string; WebSocketImpl?: typeof WebSocket});
  connect(): Promise<void>;
  call(op: string, request: unknown): Promise<unknown>;
  close(): void;
}

export interface PleskVerificationConfig {
  mode?: "content_hash" | "http_status" | "content_marker";
  path?: string;
  content_sha256?: string;
  expected_http_status?: number;
  marker?: string;
}

export interface PleskPublicationConfig {
  mode?: "static_httpdocs" | "release";
  publish_uri?: string;
  verify_uri?: string;
  source_ref: string;
  deployment_ref: string;
  verification?: PleskVerificationConfig;
  remote_path?: string;
  transport?: "auto" | "sftp";
  sftp_host?: string;
  sftp_port?: number;
  sftp_vault_entry_id?: string;
  credential_origin?: string;
  host_fingerprint?: string;
  actor?: string;
  pack_id?: string;
  pack_version?: string;
  base_url?: string;
  subscription_vault_entry_id?: string;
  runtime_vault_entry_id?: string;
  vault_url?: string;
}

export interface WellManifestProject {
  id: string;
  company: string;
  domain: string;
  subscription: string;
  dns_zone: string;
  dns_provider: string;
  dns_management_plane: string;
  dns_sync_extension?: string;
  public_ingress_mode: string;
  tunnel_mode: string;
  origin_ip: string;
  source?: string;
  entrypoint?: string;
  publication: PleskPublicationConfig;
  gates?: string[];
}

export interface ProjectRegistry {
  schema: "subactor.projects/v1";
  projects: WellManifestProject[];
  connector?: Record<string, unknown>;
  twin?: Record<string, unknown>;
}

export interface PleskPublicationPlan {
  schema: "wellmanifest.plesk-publication-plan/v1";
  id: string;
  project_id: string;
  deployment_ref: string;
  created_at?: string;
  source_ref: string;
  source_dir: string;
  entrypoint: string;
  manifest_hash: string;
  contract_ref: string;
  connector: Record<string, unknown>;
  twin: Record<string, unknown>;
  allowed_uri_processes: string[];
  required_gates: string[];
  steps: Array<Record<string, unknown>>;
  diagnostics: Diagnostic[];
}

export function validateProjectRegistry(registry: ProjectRegistry): ProjectRegistry;
export function buildPleskPublicationPlan(
  registry: ProjectRegistry,
  options: {projectId: string; sourceRefs: Record<string, string>},
): Promise<PleskPublicationPlan>;

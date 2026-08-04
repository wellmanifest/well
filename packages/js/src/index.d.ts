export type Dialect = "json" | "yaml" | "toml" | "hcl" | "typed" | "policy" | "proto3" | string;
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
  convert(source: unknown, options?: {from?: Dialect; to?: Dialect; projection?: "data" | "ir"; schema?: object | null; pretty?: boolean}): Promise<Record<string, unknown>>;
  validate(source: unknown, schema: object, options?: {dialect?: Dialect}): Promise<Record<string, unknown>>;
  execute(uri: string, payload?: unknown, options?: {mode?: string; contractRef?: string; allowedUriProcesses?: string[]; runId?: string; runtime?: RuntimeTarget}): Promise<Record<string, unknown>>;
  exchange(envelope: Envelope): Promise<Envelope>;
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

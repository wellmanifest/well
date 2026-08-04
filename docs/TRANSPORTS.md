# HTTP, WebSocket, MQTT and gRPC

## HTTP API

The reference server defaults to `:8080`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Liveness and version. |
| `GET` | `/v1/capabilities` | Dialects, operations, transports and runtimes. |
| `GET` | `/v1/runtimes` | Runtime descriptors for frontend/backend/firmware/twins. |
| `POST` | `/v1/convert` | Parse and emit another dialect. |
| `POST` | `/v1/validate` | JSON Schema validation. |
| `POST` | `/v1/negotiate` | Select a receiver-compatible format. |
| `POST` | `/v1/runtime/execute` | Execute a registered concrete URI Process. |
| `POST` | `/run` | Compatibility endpoint for the supplied `urirun` client. |
| `POST` | `/v1/envelopes` | Process a canonical envelope. |
| `GET` | `/v1/events` | Read event-store projection. |
| `WS` | `/v1/ws` | Real-time convert/validate/execute messages. |

Example conversion:

```bash
curl -fsS http://localhost:8080/v1/convert \
  -H 'content-type: application/json' \
  -d @- <<'JSON'
{
  "source": "status:\n  value: SUCCEEDED\n",
  "source_dialect": "yaml",
  "target_dialect": "json",
  "projection": "data"
}
JSON
```

## WebSocket

The client sends JSON frames:

```json
{
  "id": "browser-1",
  "op": "convert",
  "payload": {
    "source": "status:\n  value: SUCCEEDED\n",
    "source_dialect": "yaml",
    "target_dialect": "json"
  }
}
```

The server returns the same `id`, an `ok` flag, result and diagnostics. `op` can
be `convert`, `validate`, `execute` or `capabilities`.

WebSocket is useful for browser editors and live gateways, but it does not
change authorization rules. Every `execute` message still requires a contract.

## MQTT v5

The optional bridge subscribes to:

```text
wellmanifest/v1/{tenant}/request/{client}
```

It publishes to the MQTT v5 Response Topic when supplied, otherwise:

```text
wellmanifest/v1/{tenant}/response/{client}
```

Correlation Data is copied to the response. Payload is a JSON WellManifest
envelope. QoS and retained-message policy are deployment settings; commands
should not be retained by default.

Run locally after installing the `mqtt` extra:

```bash
wellmanifest-mqtt \
  --broker mqtt \
  --topic 'wellmanifest/v1/+/request/+'
```

The Compose stack includes Eclipse Mosquitto and a bridge service.

## gRPC

`proto/wellmanifest/v1/wellmanifest.proto` defines:

- unary `Convert`, `Validate`, `Execute` and `GetCapabilities`;
- bidirectional streaming `Exchange` for envelopes;
- shared diagnostics, runtime target and payload structures.

Generate Python stubs:

```bash
./scripts/generate_proto.sh
wellmanifest-grpc --port 50051
```

Other languages generate clients from the same `.proto` contract. The gRPC
server translates messages into the same Python runtime used by HTTP and WS.

## Transport mapping

| Envelope field | HTTP | WebSocket | MQTT v5 | gRPC |
|---|---|---|---|---|
| message id | body/header | frame | payload | message |
| correlation id | body/header | frame | Correlation Data + payload | message |
| reply address | request connection | socket | Response Topic | stream/call |
| content type | body | frame | Content Type + payload | enum/string field |
| contract | body/header | frame | user property/payload | message |
| diagnostics | response body | response frame | response payload | repeated field |

## Backpressure and limits

Deployments should impose frame/body limits, operation timeouts, per-contract
rate limits and bounded event retention. A constrained firmware profile should
prefer small protobuf or JSON envelopes and remote execution rather than
loading all dialect parsers locally.

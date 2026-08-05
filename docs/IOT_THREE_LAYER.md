# Three-layer IoT example

`compose.iot.yml` demonstrates one protocol across three application layers.

```text
browser frontend
    │ HTTP polling / future WebSocket
    ▼
Wellm backend + event store
    ▲
    │ shared append-only events
MQTT v5 bridge
    ▲
    │ request/response envelope + correlation data
thin firmware simulator (RPi/MCU profile)
```

## Start and stop

```bash
make setup-lite
make iot-up
# frontend: http://localhost:8090
# backend:  http://localhost:8091
# MQTT:     localhost:1884
make iot-down
```

Run the isolated test:

```bash
make iot-e2e
```

The firmware first requests
`iot://device/config/query/get`, then publishes a
`wellm.iot-telemetry/v1` command to
`iot://device/telemetry/command/ingest`. Contract AQL is resolved by the bridge;
the device cannot expand its own URI scopes. The backend and bridge share the
append-only JSONL store, and the frontend reads `TelemetryReceived` events.

## Components

| Layer | Service | Runtime | Responsibility |
|---|---|---|---|
| frontend | `frontend` | nginx + JS | read-only dashboard and backend proxy |
| backend | `backend` | Python/FastAPI | URI execution, versions, schemas, event query |
| firmware | `firmware` | Python MQTT simulator | small envelope, config query, telemetry command |
| transport | `broker` | Mosquitto 2 | MQTT v5 request/response |
| adapter | `bridge` | Wellm MQTT bridge | envelope validation, Contract AQL, receipts |

All services use the explicit `WELLMANIFEST_IOT_SUBNET`. This avoids asking
Docker to allocate another subnet from an exhausted default pool.

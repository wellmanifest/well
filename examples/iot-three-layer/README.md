# Wellm IoT — trzy warstwy

Przykład uruchamia trzy warstwy aplikacji oraz dwa elementy transportowe:

| Warstwa | Usługa | Rola |
|---|---|---|
| frontend | `frontend` | statyczny panel WWW, odczyt zdarzeń przez HTTP |
| backend | `backend` | Wellm HTTP/WS runtime, event store i kontrakty |
| firmware | `firmware` | symulator małego urządzenia/RPi, klient MQTT v5 |
| transport | `broker` | Eclipse Mosquitto |
| adapter | `bridge` | MQTT envelope → Wellm runtime → MQTT result |

```bash
make setup
make iot-up
# frontend: http://localhost:8090
# backend:  http://localhost:8091
make iot-down
```

Pełny test:

```bash
make iot-e2e
```

Firmware najpierw pobiera konfigurację przez
`iot://device/config/query/get`, a następnie wysyła telemetrię do
`iot://device/telemetry/command/ingest`. Wildcard nie jest wykonywalnym URI;
uprawnienia pochodzą z `contract:firmware-thin`.

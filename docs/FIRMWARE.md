# Firmware, Raspberry Pi and constrained devices

## Deployment profiles

| Profile | Device capability | Local components | Remote components |
|---|---|---|---|
| `firmware-thin` | MCU/MicroPython | envelope, TLS client, contract ref | parse, schema, conversion, process adapters |
| `rpi-python` | Raspberry Pi OS | Python SDK, optional local cache | full remote runtime or local Python runtime |
| `rpi-native` | Raspberry Pi Linux | Rust CLI/core | optional remote adapters and registry |
| `browser-wasm` | browser/embedded UI | WASM JSON/YAML core | policy/proto/LLM and privileged processes |
| `gateway` | edge Linux | full runtime, MQTT bridge | central contracts/events if configured |

## Thin-client pattern

```text
sensor/MCU -- MQTT/HTTP envelope --> edge WellManifest runtime
    ^                                     |
    |                                     +-- schema validation
    |                                     +-- format conversion
    |                                     +-- registered URI adapters
    +------------- compact result --------+
```

A small device sends only data and a contract/runtime declaration. It does not
download or execute arbitrary application source. This keeps memory use and the
security boundary predictable.

## Hardware configuration manifest

`examples/hardware/rpi-gpio.wm.yaml` describes a GPIO plan:

```yaml
spec: wellmanifest.hardware/v1
board: raspberry-pi-4
pins:
  - number: 17
    mode: output
    initial: low
```

The demo URI:

```text
gpio://rpi/pin/configure/plan
```

returns a plan only. A real mutating adapter should require a device-specific
contract, board detection, pin reservation and a receipt.

## Raspberry Pi client

```bash
python examples/firmware/rpi_client.py \
  --server http://runtime:8080 \
  --contract contract:firmware-thin
```

The client uses ordinary HTTP and can run without compiler toolchains on the
Pi. For offline operation install the Python package and instantiate
`WellManifestRuntime` locally.

## MicroPython

`examples/firmware/micropython_client.py` uses `urequests`/`ujson` style APIs.
It constructs a minimal execute request and sends it to a gateway. TLS
certificate verification, token storage and reconnect behavior are platform
responsibilities and must be configured for the target board.

## C envelope

`examples/firmware/c/wellmanifest_envelope.h` provides bounded structs and
constants suitable for integrating a C MQTT/HTTP stack. It is not a network
implementation; the application chooses its TLS and broker libraries.

## MQTT recommendations

- use a per-device identity and topic ACL;
- place the server-resolved contract reference in the envelope;
- use correlation data/response topic for request-response;
- bound message size and JSON nesting;
- never retain commands by default;
- deduplicate with an idempotency key stored across reconnects when effects are
  possible;
- support firmware-specific timeout and energy budgets.

## Shared server environment

A constrained client can select:

```json
{
  "runtime_ref": "runtime:firmware-thin@1",
  "environment": "firmware",
  "execution": "remote",
  "resources": {"timeout_ms": 3000, "response_bytes": 4096}
}
```

The server maps this declaration to a preinstalled runtime profile. It does not
accept arbitrary binary uploads. Multiple devices may share the runtime while
remaining isolated by tenant, contract, rate limit and event stream.

# MicroPython thin client: conversion and validation stay on the shared server.
# Requires the common `urequests` module supplied by the board firmware.
import json
import urequests

RUNTIME_URL = "http://runtime.local:8080"

request = {
    "uri": "gpio://rpi/pin/configure/plan",
    "payload": {"pin": 17, "direction": "out"},
    "contract_ref": "contract:firmware-thin",
    "run_id": "sensor-01:gpio17:plan",
    "runtime": {
        "runtime_ref": "firmware-thin",
        "environment": "firmware",
        "execution": "remote",
        "resources": {"memoryKiB": 256}
    }
}

response = urequests.post(
    RUNTIME_URL + "/v1/runtime/execute",
    data=json.dumps(request),
    headers={"content-type": "application/json"},
)
print(response.text)
response.close()

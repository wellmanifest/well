from __future__ import annotations

import json
import os
import random
import threading
import time
from pathlib import Path
from uuid import uuid4

import paho.mqtt.client as mqtt

HOST = os.getenv("WELLMANIFEST_MQTT_HOST", "broker")
PORT = int(os.getenv("WELLMANIFEST_MQTT_PORT", "1883"))
TENANT = os.getenv("WELLMANIFEST_TENANT", "default")
DEVICE_ID = os.getenv("WELLMANIFEST_IOT_DEVICE_ID", "rpi-sim-001")
INTERVAL = float(os.getenv("WELLMANIFEST_IOT_SAMPLE_INTERVAL", "1.0"))
RUN_ONCE = os.getenv("WELLMANIFEST_IOT_RUN_ONCE", "1").lower() in {"1", "true", "yes"}
CONTRACT = os.getenv("WELLMANIFEST_CONTRACT", "contract:firmware-thin")
STATE = Path("/state/firmware-result.json")
REQUEST_TOPIC = f"wellmanifest/v1/{TENANT}/request/{DEVICE_ID}"
RESPONSE_TOPIC = f"wellmanifest/v1/{TENANT}/response/{DEVICE_ID}"

received: list[dict] = []
ready = threading.Event()
response_ready = threading.Event()
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)


def on_connect(client, _userdata, _flags, reason_code, _properties):
    if int(reason_code) != 0:
        raise RuntimeError(f"mqtt_connect_failed:{reason_code}")
    client.subscribe(RESPONSE_TOPIC, qos=1)
    ready.set()


def on_message(_client, _userdata, message):
    received.append(json.loads(message.payload))
    response_ready.set()


client.on_connect = on_connect
client.on_message = on_message
for attempt in range(30):
    try:
        client.connect(HOST, PORT, 30)
        break
    except OSError:
        if attempt == 29:
            raise
        time.sleep(1)
client.loop_start()
if not ready.wait(15):
    raise SystemExit("firmware_mqtt_connect_timeout")


def execute(operation: str, payload: dict, run_id: str) -> dict:
    response_ready.clear()
    properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
    properties.ResponseTopic = RESPONSE_TOPIC
    properties.CorrelationData = run_id.encode("utf-8")
    envelope = {
        "spec": "wellmanifest.protocol/v1",
        "id": str(uuid4()),
        "kind": "command" if "/command/" in operation else "query",
        "operation": operation,
        "content_type": "application/wellmanifest+json",
        "accept": ["application/wellmanifest+json"],
        "contract_ref": CONTRACT,
        "idempotency_key": run_id,
        "runtime": {
            "runtime_ref": "runtime:firmware-thin@1",
            "environment": "firmware",
            "execution": "remote",
            "resources": {"memoryKiB": 256, "transport": "mqtt-v5"},
        },
        "payload": payload,
        "diagnostics": [],
        "metadata": {"deviceId": DEVICE_ID, "layer": "firmware"},
    }
    client.publish(REQUEST_TOPIC, json.dumps(envelope), qos=1, properties=properties)
    if not response_ready.wait(15):
        raise RuntimeError(f"firmware_response_timeout:{operation}")
    response = received[-1]
    if response.get("kind") != "result":
        raise RuntimeError(f"firmware_runtime_error:{response}")
    return response


config = execute(
    "iot://device/config/query/get",
    {"deviceId": DEVICE_ID},
    f"{DEVICE_ID}:config:1",
)
iteration = 0
while True:
    iteration += 1
    telemetry = execute(
        "iot://device/telemetry/command/ingest",
        {
            "schema": "wellm.iot-telemetry/v1",
            "deviceId": DEVICE_ID,
            "readings": {
                "temperatureC": round(21.5 + random.random() * 2.0, 2),
                "humidityPct": round(44.0 + random.random() * 4.0, 2),
            },
            "unit": {"temperatureC": "celsius", "humidityPct": "percent"},
        },
        f"{DEVICE_ID}:telemetry:{iteration}",
    )
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(
        json.dumps(
            {
                "schema": "wellm.iot-firmware-result/v1",
                "deviceId": DEVICE_ID,
                "config": config,
                "telemetry": telemetry,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"firmware sample {iteration}: acknowledged", flush=True)
    if RUN_ONCE:
        break
    time.sleep(INTERVAL)

client.loop_stop()
client.disconnect()

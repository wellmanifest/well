from __future__ import annotations

import json
import os
import threading
import time
from uuid import uuid4

import paho.mqtt.client as mqtt

host = os.getenv("MQTT_HOST", "mqtt")
request_topic = "wellmanifest/v1/default/request/e2e"
response_topic = "wellmanifest/v1/default/response/e2e"
received: list[dict] = []
done = threading.Event()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)


def on_connect(client, _userdata, _flags, reason_code, _properties):
    if reason_code.is_failure:
        raise RuntimeError(f"mqtt connect: {reason_code}")
    client.subscribe(response_topic, qos=1)


def on_message(_client, _userdata, message):
    received.append(json.loads(message.payload))
    done.set()


client.on_connect = on_connect
client.on_message = on_message
for attempt in range(30):
    try:
        client.connect(host, 1883, 30)
        break
    except OSError:
        if attempt == 29:
            raise
        time.sleep(1)
client.loop_start()
for _ in range(30):
    if client.is_connected():
        break
    time.sleep(0.2)

properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
properties.ResponseTopic = response_topic
properties.CorrelationData = b"mqtt-e2e-1"
envelope = {
    "spec": "wellmanifest.protocol/v1",
    "id": str(uuid4()),
    "kind": "query",
    "operation": "youtube://channel/video/query/list",
    "content_type": "application/wellmanifest+json",
    "accept": ["application/wellmanifest+json"],
    "contract_ref": "contract:dev",
    "idempotency_key": "docker-mqtt:youtube:1",
    "runtime": {
        "runtime_ref": "runtime:firmware-thin@1",
        "environment": "iot",
        "execution": "remote",
        "resources": {},
    },
    "payload": {"channel": "ours"},
    "diagnostics": [],
    "metadata": {},
}
client.publish(request_topic, json.dumps(envelope), qos=1, properties=properties)
if not done.wait(15):
    raise SystemExit("mqtt e2e timeout")
client.loop_stop()
client.disconnect()
assert received[0]["kind"] == "result", received[0]
print("mqtt e2e: PASS")

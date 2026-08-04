from __future__ import annotations

import json
import os
import signal
import sys
from typing import Any

from .models import Envelope
from .runtime import WellManifestRuntime


def main() -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit("Install `wellmanifest[mqtt]` to run the MQTT bridge") from exc

    host = os.getenv("WELLMANIFEST_MQTT_HOST", "mqtt")
    port = int(os.getenv("WELLMANIFEST_MQTT_PORT", "1883"))
    tenant = os.getenv("WELLMANIFEST_TENANT", "default")
    request_topic = os.getenv("WELLMANIFEST_MQTT_REQUEST_TOPIC", f"wellmanifest/v1/{tenant}/request/#")
    runtime = WellManifestRuntime()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    username = os.getenv("WELLMANIFEST_MQTT_USERNAME", "")
    password = os.getenv("WELLMANIFEST_MQTT_PASSWORD", "")
    if username:
        client.username_pw_set(username, password)

    def on_connect(client: Any, _userdata: Any, _flags: Any, reason_code: Any, _properties: Any) -> None:
        if int(reason_code) != 0:
            print(f"MQTT connect failed: {reason_code}", file=sys.stderr)
            return
        client.subscribe(request_topic, qos=1)
        print(f"WellManifest MQTT bridge subscribed to {request_topic}")

    def on_message(client: Any, _userdata: Any, message: Any) -> None:
        response_topic = None
        correlation_data = None
        properties = getattr(message, "properties", None)
        if properties is not None:
            response_topic = getattr(properties, "ResponseTopic", None)
            correlation_data = getattr(properties, "CorrelationData", None)
        try:
            envelope = Envelope.model_validate_json(message.payload)
            response = runtime.exchange(envelope)
            output = response.model_dump_json().encode("utf-8")
            target_topic = response_topic or f"wellmanifest/v1/{tenant}/response/{envelope.id}"
            response_properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
            if correlation_data is not None:
                response_properties.CorrelationData = correlation_data
            client.publish(target_topic, output, qos=1, properties=response_properties)
        except Exception as exc:
            target_topic = response_topic or f"wellmanifest/v1/{tenant}/diagnostic/bridge"
            diagnostic = {
                "spec": "wellmanifest.protocol/v1",
                "kind": "diagnostic",
                "operation": "wellmanifest://mqtt/bridge/error",
                "payload": {},
                "diagnostics": [{"code": "WM-MQTT-500", "severity": "ERROR", "message": str(exc)}],
            }
            client.publish(target_topic, json.dumps(diagnostic).encode("utf-8"), qos=1)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, keepalive=60)

    def stop(_signum: int, _frame: Any) -> None:
        client.disconnect()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    client.loop_forever()


if __name__ == "__main__":
    main()

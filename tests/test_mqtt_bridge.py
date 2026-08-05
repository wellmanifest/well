from __future__ import annotations

from wellmanifest.mqtt_bridge import _mqtt_connect_failed


class PahoReasonCode:
    def __init__(self, is_failure: bool) -> None:
        self.is_failure = is_failure


def test_mqtt_connect_failed_supports_paho_v2_reason_codes() -> None:
    assert not _mqtt_connect_failed(PahoReasonCode(False))
    assert _mqtt_connect_failed(PahoReasonCode(True))


def test_mqtt_connect_failed_supports_legacy_integer_codes() -> None:
    assert not _mqtt_connect_failed(0)
    assert _mqtt_connect_failed(1)


def test_mqtt_connect_failed_fails_closed_for_unknown_values() -> None:
    assert _mqtt_connect_failed(object())

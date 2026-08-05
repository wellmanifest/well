from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from wellmanifest.env_contract import setup_env, verify_env_contract
from wellmanifest.runtime import WellManifestRuntime
from wellmanifest.versions import build_version_registry

ROOT = Path(__file__).resolve().parents[1]


def test_version_registry_tracks_formats_apis_schemas_and_packages() -> None:
    registry = build_version_registry(ROOT)
    dialects = {item["id"] for item in registry["dialects"]}
    api_ids = {item["id"] for item in registry["apis"]}
    schema_paths = {item["path"] for item in registry["schemas"]}
    assert {"json@rfc8259", "yaml@1.2/json-compatible", "typed@1", "hcl@2", "toon@1"} <= dialects
    assert {"wellm-http-api", "wellm-websocket-api", "wellm-mqtt-api", "wellm-grpc-api"} <= api_ids
    assert "schemas/intent-format-analysis.schema.json" in schema_paths
    assert all(item["sha256"].startswith("sha256:") for item in registry["schemas"])
    assert all(item["version"] and item["compatibility"] in {"exact-major", "exact-hash"} for item in registry["schemas"])
    assert not any(item["path"].endswith("openapi.json") for item in registry["schemas"])
    assert registry["package"]["version"] == "0.2.0rc4"


def test_env_contract_is_single_source_and_setup_is_idempotent(tmp_path: Path) -> None:
    # The repository contract must cover every product-owned env reference.
    report = verify_env_contract(ROOT)
    assert report["ok"], report["errors"]
    # Setup never overwrites an existing local file unless force is explicit.
    (tmp_path / "config").mkdir()
    (tmp_path / "schemas").mkdir()
    (tmp_path / "src" / "wellmanifest" / "resources").mkdir(parents=True)
    (tmp_path / "config" / "env-contract.json").write_text((ROOT / "config" / "env-contract.json").read_text())
    (tmp_path / "schemas" / "env-contract.schema.json").write_text((ROOT / "schemas" / "env-contract.schema.json").read_text())
    path = setup_env(tmp_path)
    original = path.read_text()
    path.write_text(original + "# local\n")
    assert setup_env(tmp_path).read_text().endswith("# local\n")


def test_iot_runtime_config_and_telemetry_are_contract_guarded() -> None:
    runtime = WellManifestRuntime()
    config = runtime.execute_uri(
        {
            "uri": "iot://device/config/query/get",
            "contract_ref": "contract:firmware-thin",
            "run_id": "iot:config:1",
            "payload": {"deviceId": "rpi-sim-001"},
        }
    )
    assert config.ok
    assert config.result["value"]["schema"] == "wellm.iot-device-config/v1"
    assert config.result["value"]["runtime"] == "runtime:firmware-thin@1"
    config_schema = json.loads((ROOT / "schemas" / "iot-device-config.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(config_schema).validate(config.result["value"])
    telemetry = runtime.execute_uri(
        {
            "uri": "iot://device/telemetry/command/ingest",
            "contract_ref": "contract:firmware-thin",
            "run_id": "iot:telemetry:1",
            "payload": {
                "schema": "wellm.iot-telemetry/v1",
                "deviceId": "rpi-sim-001",
                "readings": {"temperature": 21.5, "humidity": 48},
            },
        }
    )
    assert telemetry.ok
    assert telemetry.result["value"]["accepted"] == ["humidity", "temperature"]
    telemetry_schema = json.loads((ROOT / "schemas" / "iot-telemetry.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(telemetry_schema).validate({
        "schema": "wellm.iot-telemetry/v1",
        "deviceId": "rpi-sim-001",
        "readings": {"temperature": 21.5, "humidity": 48},
    })
    assert any(event["type"] == "TelemetryReceived" for event in runtime.events.read(stream="device:rpi-sim-001"))


def test_three_layer_compose_and_make_targets_are_present() -> None:
    compose = yaml.safe_load((ROOT / "compose.iot.yml").read_text(encoding="utf-8"))
    assert {"frontend", "backend", "firmware", "bridge", "broker", "iot-e2e"} <= set(compose["services"])
    assert compose["networks"]["iot"]["ipam"]["config"][0]["subnet"].startswith("${WELLMANIFEST_IOT_SUBNET")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("setup:", "up:", "down:", "iot-up:", "iot-down:", "e2e:"):
        assert target in makefile


def test_packaged_version_registry_check_does_not_require_source_tree(tmp_path, monkeypatch) -> None:
    import wellmanifest.versions as versions

    monkeypatch.setattr(versions, "_root_from_module", lambda: tmp_path)
    registry = versions.sync_version_registry(check=True)
    assert len(registry["apis"]) == 4
    assert all(item["sha256"].startswith("sha256:") for item in registry["apis"])

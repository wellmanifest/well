from __future__ import annotations

import ipaddress
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from docker_network_preflight import (  # noqa: E402
    DEFAULTS,
    allocate_port_repairs,
    allocate_repairs,
    find_collisions,
    find_port_collisions,
    read_dotenv,
    resolve_requested,
    write_dotenv,
)


def network(value: str) -> ipaddress.IPv4Network:
    parsed = ipaddress.ip_network(value)
    assert isinstance(parsed, ipaddress.IPv4Network)
    return parsed


def test_repairs_defaults_overlapping_existing_supernet() -> None:
    selected = list(DEFAULTS)
    requested, sources = resolve_requested(selected, {}, {})
    existing = [
        ("mcp_mcp-internal", network("172.30.0.0/16")),
        ("subactor-platform-net", network("10.240.0.0/24")),
    ]

    collisions = find_collisions(requested, existing)
    repairs, blocked = allocate_repairs(requested, sources, collisions, existing)

    assert set(repairs) == set(DEFAULTS)
    assert not blocked
    assert len(set(repairs.values())) == 4
    assert all(
        not candidate.overlaps(occupied)
        for candidate in repairs.values()
        for _, occupied in existing
    )


def test_process_override_remains_fail_closed() -> None:
    selected = ["WELLMANIFEST_PUBLIC_SUBNET"]
    requested, sources = resolve_requested(
        selected, {}, {"WELLMANIFEST_PUBLIC_SUBNET": "172.30.240.0/24"}
    )
    existing = [("foreign", network("172.30.0.0/16"))]

    repairs, blocked = allocate_repairs(
        requested, sources, find_collisions(requested, existing), existing
    )

    assert repairs == {}
    assert blocked == ["WELLMANIFEST_PUBLIC_SUBNET"]


def test_expected_compose_network_is_reusable() -> None:
    requested = {"WELLMANIFEST_PUBLIC_SUBNET": network("10.250.1.0/24")}
    existing = [("wellmanifest_public", network("10.250.1.0/24"))]
    assert find_collisions(requested, existing) == []


def test_dotenv_update_is_atomic_and_preserves_other_values(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("TOKEN=preserve\nWELLMANIFEST_PUBLIC_SUBNET=old\n", encoding="utf-8")

    write_dotenv(
        dotenv,
        {
            "WELLMANIFEST_PUBLIC_SUBNET": "10.240.1.0/24",
            "WELLMANIFEST_RUNTIME_SUBNET": "10.240.2.0/24",
        },
    )

    values = read_dotenv(dotenv)
    assert values["TOKEN"] == "preserve"
    assert values["WELLMANIFEST_PUBLIC_SUBNET"] == "10.240.1.0/24"
    assert values["WELLMANIFEST_RUNTIME_SUBNET"] == "10.240.2.0/24"
    assert dotenv.stat().st_mode & 0o777 == 0o600


def test_repairs_foreign_container_and_host_listener_ports() -> None:
    requested = {
        "WELLMANIFEST_HTTP_HOST_PORT": 8080,
        "WELLMANIFEST_GRPC_HOST_PORT": 50051,
        "WELLMANIFEST_MQTT_HOST_PORT": 1883,
    }
    sources = {name: "default" for name in requested}
    occupied = {
        8080: {"foreign-web"},
        1883: {"wellmanifest-mqtt-1"},
    }

    def bindable(port: int) -> bool:
        return port != 50051

    collisions = find_port_collisions(requested, occupied, bindable)
    repairs, blocked = allocate_port_repairs(
        requested, sources, collisions, occupied, bindable
    )

    assert set(repairs) == {
        "WELLMANIFEST_HTTP_HOST_PORT",
        "WELLMANIFEST_GRPC_HOST_PORT",
    }
    assert repairs["WELLMANIFEST_HTTP_HOST_PORT"] == 20000
    assert repairs["WELLMANIFEST_GRPC_HOST_PORT"] == 20001
    assert not blocked


def test_process_port_override_remains_fail_closed() -> None:
    requested = {"WELLMANIFEST_HTTP_HOST_PORT": 8080}
    sources = {"WELLMANIFEST_HTTP_HOST_PORT": "process"}
    occupied = {8080: {"foreign-web"}}
    collisions = find_port_collisions(requested, occupied, lambda _: False)
    repairs, blocked = allocate_port_repairs(
        requested, sources, collisions, occupied, lambda _: True
    )
    assert repairs == {}
    assert blocked == ["WELLMANIFEST_HTTP_HOST_PORT"]

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "WELLMANIFEST_PUBLIC_SUBNET": "172.30.240.0/24",
    "WELLMANIFEST_RUNTIME_SUBNET": "172.30.241.0/24",
    "WELLMANIFEST_E2E_SUBNET": "172.30.242.0/24",
    "WELLMANIFEST_IOT_SUBNET": "172.30.243.0/24",
}
SCOPES = {
    "main": ["WELLMANIFEST_PUBLIC_SUBNET", "WELLMANIFEST_RUNTIME_SUBNET"],
    "e2e": ["WELLMANIFEST_E2E_SUBNET"],
    "iot": ["WELLMANIFEST_IOT_SUBNET"],
    "all": list(DEFAULTS),
}
HOST_PORT_DEFAULTS = {
    "WELLMANIFEST_HTTP_HOST_PORT": 8080,
    "WELLMANIFEST_GRPC_HOST_PORT": 50051,
    "WELLMANIFEST_MQTT_HOST_PORT": 1883,
    "WELLMANIFEST_WWW_HOST_PORT": 8088,
    "WELLMANIFEST_IOT_FRONTEND_PORT": 8090,
    "WELLMANIFEST_IOT_BACKEND_PORT": 8091,
    "WELLMANIFEST_IOT_MQTT_PORT": 1884,
}
SCOPE_PORTS = {
    "main": [
        "WELLMANIFEST_HTTP_HOST_PORT",
        "WELLMANIFEST_GRPC_HOST_PORT",
        "WELLMANIFEST_MQTT_HOST_PORT",
        "WELLMANIFEST_WWW_HOST_PORT",
    ],
    "e2e": [],
    "iot": [
        "WELLMANIFEST_IOT_FRONTEND_PORT",
        "WELLMANIFEST_IOT_BACKEND_PORT",
        "WELLMANIFEST_IOT_MQTT_PORT",
    ],
    "all": list(HOST_PORT_DEFAULTS),
}
EXPECTED_CONTAINERS = {
    "WELLMANIFEST_HTTP_HOST_PORT": "wellmanifest-runtime-1",
    "WELLMANIFEST_GRPC_HOST_PORT": "wellmanifest-grpc-1",
    "WELLMANIFEST_MQTT_HOST_PORT": "wellmanifest-mqtt-1",
    "WELLMANIFEST_WWW_HOST_PORT": "wellmanifest-www-1",
    "WELLMANIFEST_IOT_FRONTEND_PORT": "wellmanifest-iot-frontend-1",
    "WELLMANIFEST_IOT_BACKEND_PORT": "wellmanifest-iot-backend-1",
    "WELLMANIFEST_IOT_MQTT_PORT": "wellmanifest-iot-broker-1",
}
EXPECTED_NETWORKS = {
    "WELLMANIFEST_PUBLIC_SUBNET": "wellmanifest_public",
    "WELLMANIFEST_RUNTIME_SUBNET": "wellmanifest_runtime",
    "WELLMANIFEST_E2E_SUBNET": "wellmanifest-e2e_e2e",
    "WELLMANIFEST_IOT_SUBNET": "wellmanifest-iot_iot",
}
CANDIDATE_POOLS = (
    ipaddress.ip_network("10.240.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
)


def run_json(command: list[str]) -> Any:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return json.loads(result.stdout or "[]")


def read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"invalid dotenv line {number}: expected NAME=value")
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()
    return values


def resolve_requested(
    selected: list[str], dotenv: dict[str, str], environment: dict[str, str]
) -> tuple[dict[str, ipaddress.IPv4Network], dict[str, str]]:
    requested: dict[str, ipaddress.IPv4Network] = {}
    sources: dict[str, str] = {}
    for name in selected:
        if name in environment:
            raw, source = environment[name], "process"
        elif name in dotenv:
            raw, source = dotenv[name], "dotenv"
        else:
            raw, source = DEFAULTS[name], "default"
        network = ipaddress.ip_network(raw, strict=False)
        if not isinstance(network, ipaddress.IPv4Network):
            raise ValueError(f"{name} must be an IPv4 CIDR")
        requested[name] = network
        sources[name] = source
    return requested, sources


def resolve_ports(
    selected: list[str], dotenv: dict[str, str], environment: dict[str, str]
) -> tuple[dict[str, int], dict[str, str]]:
    requested: dict[str, int] = {}
    sources: dict[str, str] = {}
    for name in selected:
        if name in environment:
            raw, source = environment[name], "process"
        elif name in dotenv:
            raw, source = dotenv[name], "dotenv"
        else:
            raw, source = str(HOST_PORT_DEFAULTS[name]), "default"
        try:
            port = int(raw)
        except ValueError as error:
            raise ValueError(f"{name} must be an integer port") from error
        if not 1 <= port <= 65535:
            raise ValueError(f"{name} must be between 1 and 65535")
        requested[name] = port
        sources[name] = source
    return requested, sources


def docker_networks(docker: str) -> list[tuple[str, ipaddress.IPv4Network]]:
    ids = subprocess.run(
        [docker, "network", "ls", "-q"], check=True, text=True, capture_output=True
    ).stdout.split()
    networks = run_json([docker, "network", "inspect", *ids]) if ids else []
    existing: list[tuple[str, ipaddress.IPv4Network]] = []
    for item in networks:
        name = str(item.get("Name", ""))
        for config in item.get("IPAM", {}).get("Config", []) or []:
            subnet = config.get("Subnet")
            if not subnet:
                continue
            try:
                parsed = ipaddress.ip_network(subnet, strict=False)
            except ValueError:
                continue
            if isinstance(parsed, ipaddress.IPv4Network):
                existing.append((name, parsed))
    return existing


def docker_host_ports(docker: str) -> dict[int, set[str]]:
    ids = subprocess.run(
        [docker, "ps", "-q"], check=True, text=True, capture_output=True
    ).stdout.split()
    containers = run_json([docker, "inspect", *ids]) if ids else []
    occupied: dict[int, set[str]] = {}
    for item in containers:
        name = str(item.get("Name", "")).removeprefix("/")
        for bindings in (item.get("NetworkSettings", {}).get("Ports", {}) or {}).values():
            for binding in bindings or []:
                raw = binding.get("HostPort")
                if raw:
                    occupied.setdefault(int(raw), set()).add(name)
    return occupied


def port_is_bindable(port: int) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("0.0.0.0", port))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def find_port_collisions(
    requested: dict[str, int],
    occupied: dict[int, set[str]],
    bindable: Any = port_is_bindable,
) -> list[dict[str, Any]]:
    collisions: list[dict[str, Any]] = []
    items = list(requested.items())
    for index, (variable, port) in enumerate(items):
        owners = occupied.get(port, set())
        expected = EXPECTED_CONTAINERS[variable]
        foreign = sorted(owner for owner in owners if owner != expected)
        if foreign:
            collisions.append(
                {"variable": variable, "requested": port, "owners": foreign}
            )
        elif not owners and not bindable(port):
            collisions.append(
                {"variable": variable, "requested": port, "owners": ["host-listener"]}
            )
        for other_variable, other_port in items[:index]:
            if port == other_port:
                collisions.append(
                    {
                        "variable": variable,
                        "requested": port,
                        "owners": [f"requested:{other_variable}"],
                    }
                )
    return collisions


def find_collisions(
    requested: dict[str, ipaddress.IPv4Network],
    existing: list[tuple[str, ipaddress.IPv4Network]],
) -> list[dict[str, str]]:
    collisions: list[dict[str, str]] = []
    items = list(requested.items())
    for index, (variable, subnet) in enumerate(items):
        expected_name = EXPECTED_NETWORKS[variable]
        for name, occupied in existing:
            if name == expected_name and occupied == subnet:
                continue
            if subnet.overlaps(occupied):
                collisions.append(
                    {
                        "variable": variable,
                        "requested": str(subnet),
                        "network": name,
                        "occupied": str(occupied),
                    }
                )
        for other_variable, other_subnet in items[:index]:
            if subnet.overlaps(other_subnet):
                collisions.append(
                    {
                        "variable": variable,
                        "requested": str(subnet),
                        "network": f"requested:{other_variable}",
                        "occupied": str(other_subnet),
                    }
                )
    return collisions


def allocate_repairs(
    requested: dict[str, ipaddress.IPv4Network],
    sources: dict[str, str],
    collisions: list[dict[str, str]],
    existing: list[tuple[str, ipaddress.IPv4Network]],
) -> tuple[dict[str, ipaddress.IPv4Network], list[str]]:
    colliding = {item["variable"] for item in collisions}
    repairable = sorted(name for name in colliding if sources[name] != "process")
    blocked = sorted(name for name in colliding if sources[name] == "process")
    occupied = [network for _, network in existing]
    occupied.extend(network for name, network in requested.items() if name not in repairable)
    repairs: dict[str, ipaddress.IPv4Network] = {}
    candidates = (
        candidate
        for pool in CANDIDATE_POOLS
        for candidate in pool.subnets(new_prefix=24)
    )
    for name in repairable:
        for candidate in candidates:
            if all(not candidate.overlaps(other) for other in occupied):
                repairs[name] = candidate
                occupied.append(candidate)
                break
        else:
            raise RuntimeError("no collision-free /24 remains in configured candidate pools")
    return repairs, blocked


def allocate_port_repairs(
    requested: dict[str, int],
    sources: dict[str, str],
    collisions: list[dict[str, Any]],
    occupied: dict[int, set[str]],
    bindable: Any = port_is_bindable,
) -> tuple[dict[str, int], list[str]]:
    colliding = {str(item["variable"]) for item in collisions}
    repairable = [name for name in requested if name in colliding and sources[name] != "process"]
    blocked = sorted(name for name in colliding if sources[name] == "process")
    reserved = set(occupied)
    reserved.update(port for name, port in requested.items() if name not in repairable)
    repairs: dict[str, int] = {}
    candidates = iter(range(20000, 30000))
    for name in repairable:
        for candidate in candidates:
            if candidate not in reserved and bindable(candidate):
                repairs[name] = candidate
                reserved.add(candidate)
                break
        else:
            raise RuntimeError("no collision-free host port remains in range 20000-29999")
    return repairs, blocked


def write_dotenv(path: Path, replacements: dict[str, str]) -> None:
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    remaining = dict(replacements)
    lines: list[str] = []
    for raw in original.splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in raw:
            name = raw.split("=", 1)[0].strip()
            if name in remaining:
                lines.append(f"{name}={remaining.pop(name)}")
                continue
        lines.append(raw)
    if remaining:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append("# Selected by scripts/docker_network_preflight.py --repair")
        lines.extend(f"{name}={remaining[name]}" for name in sorted(remaining))
    content = "\n".join(lines).rstrip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check and optionally repair explicit Wellm Docker subnets before Compose creates networks"
    )
    parser.add_argument("--scope", choices=list(SCOPES), default="all")
    parser.add_argument("--dotenv", default=str(ROOT / ".env"))
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()
    docker = shutil.which("docker")
    if not docker:
        message = {
            "schema": "wellm.docker-network-preflight/v1",
            "ok": False,
            "code": "WM-DOCKER-001",
            "message": "docker command is not available",
        }
        print(json.dumps(message, indent=2))
        raise SystemExit(0 if args.allow_missing else 2)
    try:
        subprocess.run(
            [docker, "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        print(
            json.dumps(
                {
                    "schema": "wellm.docker-network-preflight/v1",
                    "ok": False,
                    "code": "WM-DOCKER-002",
                    "message": "Docker Engine is not running",
                },
                indent=2,
            )
        )
        raise SystemExit(0 if args.allow_missing else 2)

    dotenv_path = Path(args.dotenv).resolve()
    try:
        dotenv = read_dotenv(dotenv_path)
        requested, sources = resolve_requested(SCOPES[args.scope], dotenv, os.environ)
        requested_ports, port_sources = resolve_ports(SCOPE_PORTS[args.scope], dotenv, os.environ)
    except ValueError as error:
        print(
            json.dumps(
                {
                    "schema": "wellm.docker-network-preflight/v1",
                    "ok": False,
                    "code": "WM-DOCKER-003",
                    "message": str(error),
                },
                indent=2,
            )
        )
        raise SystemExit(1) from error

    existing = docker_networks(docker)
    occupied_ports = docker_host_ports(docker)
    collisions = find_collisions(requested, existing)
    port_collisions = find_port_collisions(requested_ports, occupied_ports)
    repairs: dict[str, str] = {}
    port_repairs: dict[str, int] = {}
    blocked: list[str] = []
    blocked_ports: list[str] = []
    if args.repair and collisions:
        allocated, blocked = allocate_repairs(requested, sources, collisions, existing)
        if allocated:
            repairs = {name: str(network) for name, network in allocated.items()}
            write_dotenv(dotenv_path, repairs)
            dotenv.update(repairs)
            requested, sources = resolve_requested(SCOPES[args.scope], dotenv, os.environ)
            collisions = find_collisions(requested, existing)
    if args.repair and port_collisions:
        port_repairs, blocked_ports = allocate_port_repairs(
            requested_ports, port_sources, port_collisions, occupied_ports
        )
        if port_repairs:
            write_dotenv(dotenv_path, {name: str(port) for name, port in port_repairs.items()})
            dotenv.update({name: str(port) for name, port in port_repairs.items()})
            requested_ports, port_sources = resolve_ports(
                SCOPE_PORTS[args.scope], dotenv, os.environ
            )
            port_collisions = find_port_collisions(requested_ports, occupied_ports)

    report = {
        "schema": "wellm.docker-network-preflight/v1",
        "ok": not collisions and not port_collisions,
        "scope": args.scope,
        "dotenv": str(dotenv_path),
        "explicitSubnets": {key: str(value) for key, value in requested.items()},
        "sources": sources,
        "repairs": repairs,
        "blockedProcessOverrides": blocked,
        "collisions": collisions,
        "explicitHostPorts": requested_ports,
        "hostPortSources": port_sources,
        "hostPortRepairs": port_repairs,
        "blockedProcessPortOverrides": blocked_ports,
        "hostPortCollisions": port_collisions,
        "note": (
            "Compose and preflight resolve the same .env values. Use --repair to select "
            "free /24 networks and host ports; process-level overrides remain fail-closed."
        ),
    }
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()

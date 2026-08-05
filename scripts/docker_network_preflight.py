#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import shutil
import subprocess
import sys
from typing import Any

DEFAULTS = {
    "WELLMANIFEST_PUBLIC_SUBNET": "172.30.240.0/24",
    "WELLMANIFEST_RUNTIME_SUBNET": "172.30.241.0/24",
    "WELLMANIFEST_E2E_SUBNET": "172.30.242.0/24",
    "WELLMANIFEST_IOT_SUBNET": "172.30.243.0/24",
}


def run_json(command: list[str]) -> Any:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return json.loads(result.stdout or "[]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check explicit Wellm Docker subnets before Compose creates networks")
    parser.add_argument("--scope", choices=["main", "e2e", "iot", "all"], default="all")
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()
    docker = shutil.which("docker")
    if not docker:
        message = {"schema": "wellm.docker-network-preflight/v1", "ok": False, "code": "WM-DOCKER-001", "message": "docker command is not available"}
        print(json.dumps(message, indent=2))
        raise SystemExit(0 if args.allow_missing else 2)
    try:
        subprocess.run([docker, "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print(json.dumps({"schema": "wellm.docker-network-preflight/v1", "ok": False, "code": "WM-DOCKER-002", "message": "Docker Engine is not running"}, indent=2))
        raise SystemExit(0 if args.allow_missing else 2)

    selected = {
        "main": ["WELLMANIFEST_PUBLIC_SUBNET", "WELLMANIFEST_RUNTIME_SUBNET"],
        "e2e": ["WELLMANIFEST_E2E_SUBNET"],
        "iot": ["WELLMANIFEST_IOT_SUBNET"],
        "all": list(DEFAULTS),
    }[args.scope]
    requested = {name: ipaddress.ip_network(os.getenv(name, default), strict=False) for name, default in DEFAULTS.items() if name in selected}
    ids = subprocess.run([docker, "network", "ls", "-q"], check=True, text=True, capture_output=True).stdout.split()
    networks = run_json([docker, "network", "inspect", *ids]) if ids else []
    existing: list[tuple[str, ipaddress._BaseNetwork]] = []
    for item in networks:
        name = str(item.get("Name", ""))
        for config in item.get("IPAM", {}).get("Config", []) or []:
            subnet = config.get("Subnet")
            if subnet:
                try:
                    existing.append((name, ipaddress.ip_network(subnet, strict=False)))
                except ValueError:
                    pass
    collisions = []
    allowed_prefixes = ("wellmanifest_", "wellmanifest-e2e_", "wellmanifest-iot_", "wellm-")
    for variable, subnet in requested.items():
        for name, occupied in existing:
            if subnet.overlaps(occupied) and not name.startswith(allowed_prefixes):
                collisions.append({"variable": variable, "requested": str(subnet), "network": name, "occupied": str(occupied)})
    report = {
        "schema": "wellm.docker-network-preflight/v1",
        "ok": not collisions,
        "scope": args.scope,
        "explicitSubnets": {key: str(value) for key, value in requested.items()},
        "collisions": collisions,
        "note": "Explicit IPAM subnets avoid Docker's exhausted predefined address-pool allocator. Change the corresponding .env CIDR if a collision is reported.",
    }
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()

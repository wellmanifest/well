#!/usr/bin/env python3
"""Dependency-free Raspberry Pi/edge thin client."""
from __future__ import annotations

import argparse
import json
import os
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default=os.getenv("WELLMANIFEST_URL", "http://localhost:8080"))
    parser.add_argument("--contract", default=os.getenv("WELLMANIFEST_CONTRACT", "contract:firmware-thin"))
    parser.add_argument("--token", default=os.getenv("WELLMANIFEST_TOKEN", ""))
    args = parser.parse_args()

    payload = {
        "uri": "gpio://rpi/pin/configure/plan",
        "payload": {"pin": 17, "direction": "out", "initial": "low"},
        "contract_ref": args.contract,
        "run_id": "rpi-01:gpio17:plan",
        "runtime": {
            "runtime_ref": "runtime:firmware-thin@1",
            "environment": "rpi",
            "execution": "remote",
            "resources": {"timeout_ms": 3000, "response_bytes": 4096},
        },
    }
    headers = {"content-type": "application/json", "accept": "application/json"}
    if args.token:
        headers["x-wellmanifest-token"] = args.token
    request = urllib.request.Request(
        args.server.rstrip("/") + "/v1/runtime/execute",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise SystemExit(json.dumps(result, ensure_ascii=False))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

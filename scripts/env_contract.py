#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wellmanifest.env_contract import setup_env, sync_env_contract, verify_env_contract  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["sync", "check", "setup"])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dotenv")
    args = parser.parse_args()
    if args.command == "sync":
        sync_env_contract(ROOT)
        print("environment contract synchronized")
        return
    if args.command == "setup":
        path = setup_env(ROOT, force=args.force)
        print(path)
        return
    report = verify_env_contract(ROOT, dotenv=args.dotenv)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()

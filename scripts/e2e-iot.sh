#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PYTHONPATH=src python3 scripts/docker_network_preflight.py --scope iot
cleanup() {
  docker compose --env-file .env -f compose.iot.yml --profile e2e down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
docker compose --env-file .env -f compose.iot.yml --profile e2e up --build --abort-on-container-exit --exit-code-from iot-e2e
